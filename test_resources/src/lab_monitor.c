#include "io.h"
#include "power.h"
#include "trap.h"
#include <stdint.h>

#define TASKS 4
#define IDLE TASKS
#define SLICE 4096ull
#define TP_VALUE(id) (0x11220000ull + (uint64_t)(id))
#define MTIME (*(volatile uint64_t *)0x0200bff8ull)
#define MTIMECMP (*(volatile uint64_t *)0x02004000ull)
#define MPP (3ull << 11)
#define MPIE (1ull << 7)
enum { UNUSED, READY, SLEEPING, DEAD };
enum { PUTCHAR = 1, SLEEP, SPAWN, EXIT, YIELD, CHECK, GETTIME };

typedef struct {
    TrapContext context;
    uint64_t wake;
    int state, priority, timer_ticks;
} Task;

static Task tasks[TASKS + 1];
static _Alignas(16) unsigned char stacks[TASKS + 1][8192];
static _Alignas(16) unsigned char kernel_stack[16384];
static int current, ecall_seen, skip_seen, kill_seen, spawn_seen;
static int priority_seen, fair_switches, idle_entries, wakeups, exits, yields;
static uint64_t slice_deadline;
static volatile uint64_t high_started, high_woke;
extern char starttext[], endtext[], lab_fault_skip[], lab_fault_kill[];

static __attribute__((noreturn)) void failure(const char *reason) {
    printf("MONITOR FAIL: %s task=%d mcause=%llx mepc=%llx mtval=%llx\n", reason,
           current, (unsigned long long)read_csr_mcause(),
           (unsigned long long)read_csr_mepc(), (unsigned long long)read_csr_mtval());
    PowerOff();
    __builtin_unreachable();
}

static void require(int condition, const char *reason) {
    if (!condition) failure(reason);
}

static void copy_context(TrapContext *to, const TrapContext *from) {
    for (unsigned i = 0; i < 32; ++i) to->x[i] = from->x[i];
    to->mstatus = from->mstatus;
    to->mepc = from->mepc;
}

static long service(long number, uint64_t argument) {
    register long a0 __asm__("a0") = (long)argument;
    register long a7 __asm__("a7") = number;
    __asm__ volatile ("ecall" : "+r"(a0) : "r"(a7) : "memory");
    return a0;
}

static uint64_t user_tp(void) {
    uint64_t value;
    __asm__ volatile ("mv %0, tp" : "=r"(value));
    return value;
}

static __attribute__((noreturn)) void task_return(void) {
    service(EXIT, 0);
    __builtin_unreachable();
}

static __attribute__((noreturn)) void worker(uint64_t id) {
    service(CHECK, user_tp() == TP_VALUE(id));
    service(PUTCHAR, 'A' + id);
    if (id == 0) {
        long child = service(SPAWN, 2);
        // The higher-priority child must have run before spawn returns to us.
        service(CHECK, child == 2 && high_started == 1);
    }
    volatile uint64_t sum = 0;
    for (uint64_t i = 0; i < 20000; ++i) sum += i;
    service(CHECK, sum == 199990000ull && user_tp() == TP_VALUE(id));
    service(YIELD, 0);
    uint64_t before = (uint64_t)service(GETTIME, 0);
    service(SLEEP, SLICE * 32);
    uint64_t after = (uint64_t)service(GETTIME, 0);
    service(CHECK, after - before >= SLICE * 32 && user_tp() == TP_VALUE(id));
    task_return();
}

static __attribute__((noreturn)) void high_task(uint64_t id) {
    service(CHECK, user_tp() == TP_VALUE(id));
    high_started = 1;
    service(PUTCHAR, 'H');
    service(SLEEP, SLICE * 2);
    high_woke = 1;
    service(CHECK, user_tp() == TP_VALUE(id));
    task_return();
}

static __attribute__((noreturn)) void fault_task(uint64_t id) {
    service(CHECK, user_tp() == TP_VALUE(id));
    __asm__ volatile (".global lab_fault_skip\nlab_fault_skip:\n.word 0xfff00073" ::: "memory");
    service(CHECK, 1); // Reached only if the first illegal instruction was skipped.
    // csrrs a0,mstatus,x0: legal in M-mode, illegal in U-mode.
    __asm__ volatile (".global lab_fault_kill\nlab_fault_kill:\n.word 0x30002573" ::: "a0", "memory");
    service(CHECK, 0); // The monitor must terminate this task instead of resuming.
    task_return();
}

static __attribute__((noreturn)) void idle_task(void) {
    for (;;) __asm__ volatile ("wfi");
}

static void initialize(int id, void (*entry)(uint64_t), int priority, int machine) {
    Task *task = &tasks[id];
    for (unsigned i = 0; i < 32; ++i) task->context.x[i] = 0;
    task->context.x[1] = (uint64_t)task_return;
    task->context.x[2] = (uint64_t)(stacks[id] + sizeof(stacks[id]));
    __asm__ volatile ("mv %0,gp" : "=r"(task->context.x[3]));
    task->context.x[4] = TP_VALUE(id);
    task->context.x[10] = (uint64_t)id;
    task->context.mepc = (uint64_t)entry;
    task->context.mstatus = MPIE | (machine ? MPP : 0);
    task->state = READY;
    task->priority = priority;
}

static void wake_sleepers(uint64_t now) {
    for (int i = 0; i < TASKS; ++i) {
        if (tasks[i].state == SLEEPING && tasks[i].wake <= now) {
            tasks[i].state = READY;
            ++wakeups;
        }
    }
}

static int choose_next(int previous) {
    int next = IDLE, best = -1;
    for (int offset = 1; offset <= TASKS; ++offset) {
        int id = (previous + offset) % TASKS;
        if (tasks[id].state == READY && tasks[id].priority > best) {
            next = id;
            best = tasks[id].priority;
        }
    }
    return next;
}

static void arm_timer(uint64_t now) {
    uint64_t deadline = current == IDLE ? UINT64_MAX : slice_deadline;
    for (int i = 0; i < TASKS; ++i)
        if (tasks[i].state == SLEEPING && tasks[i].wake < deadline) deadline = tasks[i].wake;
    MTIMECMP = deadline > now ? deadline : now + 1;
}

static __attribute__((noreturn)) void finish(void) {
    require(ecall_seen && skip_seen == 1 && kill_seen == 1, "CSR coverage");
    require(spawn_seen == 1 && exits == 3 && high_started && high_woke, "spawn/exit");
    require(priority_seen && tasks[0].timer_ticks >= 2 && tasks[1].timer_ticks >= 2
            && fair_switches >= 2, "timer fairness/priority");
    require(idle_entries && wakeups >= 3 && yields >= 2, "sleep/idle/yield");
    printf("\nCSR ECALL PASS\nCSR ILLEGAL SKIP PASS\nCSR ILLEGAL KILL PASS\n");
    printf("PREEMPT PRIORITY PASS\nROUND ROBIN PASS ticks0=%d ticks1=%d switches=%d\n",
           tasks[0].timer_ticks, tasks[1].timer_ticks, fair_switches);
    printf("SLEEP IDLE PASS entries=%d wakeups=%d\nCONTEXT TP PASS\nSPAWN EXIT PASS\nMONITOR PASS\n",
           idle_entries, wakeups);
    PowerOff();
    __builtin_unreachable();
}

void trap_handler(TrapContext *frame) {
    int previous = current, force = 0;
    uint64_t cause = read_csr_mcause(), tval = read_csr_mtval(), now = MTIME;
    require(frame->mepc >= (uint64_t)starttext && frame->mepc < (uint64_t)endtext, "trap PC range");
    require(((frame->mstatus & MPP) >> 11) == (current == IDLE ? 3 : 0), "saved privilege");
    require(frame->x[4] == TP_VALUE(current), "saved tp");
    copy_context(&tasks[current].context, frame);
    TrapContext *context = &tasks[current].context;
    if (cause == (1ull << 63 | 7)) {
        require(tval == 0, "timer mtval");
        ++tasks[current].timer_ticks;
        slice_deadline = now + SLICE;
        force = 1; // Preserve mepc: an interrupted instruction must resume unchanged.
    } else if (cause == 8) {
        require(current != IDLE && tval == 0 && *(uint32_t *)context->mepc == 0x00000073,
                "ecall CSR/instruction");
        if (!ecall_seen) printf("ECALL cause=%llx pc=%llx tval=%llx MPP=0\n",
                               (unsigned long long)cause, (unsigned long long)context->mepc,
                               (unsigned long long)tval);
        ecall_seen = 1;
        context->mepc += 4;
        uint64_t argument = context->x[10];
        switch (context->x[17]) {
        case PUTCHAR: uart_putc((char)argument); context->x[10] = 0; break;
        case SLEEP:
            tasks[current].state = SLEEPING;
            tasks[current].wake = now + argument;
            context->x[10] = 0; force = 1; break;
        case SPAWN:
            require(argument == 2 && tasks[2].state == UNUSED, "spawn request");
            initialize(2, high_task, 2, 0);
            ++spawn_seen; context->x[10] = 2; force = 1; break;
        case EXIT: tasks[current].state = DEAD; ++exits; force = 1; break;
        case YIELD: ++yields; context->x[10] = 0; force = 1; break;
        case CHECK: require(argument != 0, "user assertion"); context->x[10] = 0; break;
        case GETTIME: context->x[10] = now; break;
        default: failure("unknown ecall");
        }
    } else if (cause == 2) {
        require(current == 3, "unexpected illegal task");
        printf("ILLEGAL cause=%llx pc=%llx tval=%llx\n", (unsigned long long)cause,
               (unsigned long long)context->mepc, (unsigned long long)tval);
        if (context->mepc == (uint64_t)lab_fault_skip) {
            require(tval == 0xfff00073, "illegal skip mtval");
            ++skip_seen; context->mepc += 4;
        } else {
            require(context->mepc == (uint64_t)lab_fault_kill && tval == 0x30002573,
                    "illegal CSR PC/mtval");
            ++kill_seen; tasks[current].state = DEAD; force = 1;
        }
    } else failure("unexpected trap");

    now = MTIME;
    wake_sleepers(now);
    int living = 0;
    for (int i = 0; i < TASKS; ++i) living += tasks[i].state != DEAD && tasks[i].state != UNUSED;
    if (!living) finish();
    int next = choose_next(previous);
    if (!force && previous < TASKS && tasks[previous].state == READY
        && tasks[previous].priority >= tasks[next].priority) next = previous;
    if (cause == 8 && context->x[17] == SPAWN) {
        require(next == 2, "higher priority spawn must preempt");
        priority_seen = 1;
    }
    if (cause == (1ull << 63 | 7) && previous < 2 && next < 2 && previous != next
        && tasks[0].state == READY && tasks[1].state == READY) ++fair_switches;
    if (next != previous) {
        printf("SWITCH from=%d to=%d reason=%s priority=%d\n", previous, next,
               cause >> 63 ? "timer" : "trap", tasks[next].priority);
        if (next == IDLE) ++idle_entries;
        slice_deadline = now + SLICE;
    }
    current = next;
    arm_timer(now);
    copy_context(frame, &tasks[current].context);
    __traps_return(frame);
    __builtin_unreachable();
}

int main(void) {
    printf("MONITOR START: M-mode launches U-mode tasks\n");
    initialize(0, worker, 1, 0);
    initialize(1, worker, 1, 0);
    initialize(3, fault_task, 1, 0);
    initialize(IDLE, (void (*)(uint64_t))idle_task, -1, 1);
    write_csr_mtvec((uint64_t)__traps_entry);
    write_csr_mie(1ull << 7);
    write_csr_mscratch((uint64_t)(kernel_stack + sizeof(kernel_stack)));
    current = 0;
    slice_deadline = MTIME + SLICE;
    arm_timer(MTIME);
    TrapContext *frame = (TrapContext *)(kernel_stack + sizeof(kernel_stack) - sizeof(TrapContext));
    copy_context(frame, &tasks[0].context);
    __traps_return(frame);
    __builtin_unreachable();
}
