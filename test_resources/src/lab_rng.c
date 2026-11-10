#include "io.h"
#include "trap.h"
#include "virtio/virtio_queue.h"
#include <stdatomic.h>
#include <stdint.h>

#define REG(offset) (*(volatile uint32_t *)(0x10001000ull + (offset)))
#define PLIC(offset) (*(volatile uint32_t *)(0x0c000000ull + (offset)))
static _Alignas(16) VirtQueueDesc descriptors[8];
static _Alignas(4) unsigned char avail_memory[4 + 8 * 2 + 2];
static _Alignas(4) unsigned char used_memory[4 + 8 * 8 + 2];
static VirtQueueAvail *available = (VirtQueueAvail *)avail_memory;
static VirtQueueUsed *used = (VirtQueueUsed *)used_memory;
static unsigned char bytes[2][64];
static volatile int irq_count;

static void check(int condition, const char *reason) {
    if (!condition) { printf("RNG FAIL: %s\n", reason); PowerOff(); }
}

void trap_handler(TrapContext *context) {
    check(read_csr_mcause() == ((1ull << 63) | 11), "external IRQ cause");
    uint32_t irq = PLIC(0x200004);
    check(irq == 1 && (REG(0x60) & 1), "PLIC claim and ISR");
    REG(0x64) = 1;
    PLIC(0x200004) = irq;
    ++irq_count;
    __traps_return(context);
}

static void address(unsigned offset, uintptr_t pointer) {
    REG(offset) = (uint32_t)pointer;
    REG(offset + 4) = (uint32_t)(pointer >> 32);
}

int main(void) {
    check(REG(0) == 0x74726976 && REG(4) == 2 && REG(8) == 4, "device discovery");
    REG(0x70) = 0;
    REG(0x70) = 3;
    REG(0x14) = 1;
    check((REG(0x10) & 1) != 0, "modern version feature");
    REG(0x24) = 1; REG(0x20) = 1;
    REG(0x70) = 11;
    check((REG(0x70) & 8) != 0, "feature negotiation");
    REG(0x30) = 0; REG(0x38) = 8;
    address(0x80, (uintptr_t)descriptors);
    address(0x90, (uintptr_t)available);
    address(0xa0, (uintptr_t)used);
    REG(0x44) = 1; REG(0x70) = 15;
    PLIC(4) = 1;
    PLIC(0x2000) = 1u << 1;
    PLIC(0x200000) = 0;
    trap_init();
    write_csr_mie(1ull << 11);
    for (int round = 0; round < 2; ++round) {
        descriptors[0].paddr = (uintptr_t)bytes[round];
        descriptors[0].len = sizeof(bytes[round]);
        descriptors[0].flags = VIRTQ_DESC_F_WRITE;
        descriptors[0].next = 0;
        available->ring[round] = 0;
        atomic_store_explicit(&available->idx, round + 1, memory_order_release);
        REG(0x50) = 0;
        while (irq_count <= round) __asm__ volatile ("wfi");
        check(atomic_load_explicit(&used->idx, memory_order_acquire) == round + 1,
              "used index after interrupt");
        check(used->ring[round].id == 0 && used->ring[round].len == 64, "used id/length");
        int nonzero = 0;
        for (unsigned i = 0; i < 64; ++i) nonzero |= bytes[round][i];
        check(nonzero, "all-zero entropy smoke check");
    }
    int different = 0;
    for (unsigned i = 0; i < 64; ++i) different |= bytes[0][i] ^ bytes[1][i];
    check(different && irq_count == 2, "fresh requests and exact IRQ count");
    REG(0x70) = 0;
    check(REG(0x44) == 0 && REG(0x60) == 0, "queue/ISR reset");
    printf("RNG IRQ DMA PASS: requests=2 bytes=128 irq=%d\n", irq_count);
    pass();
    return 0;
}
