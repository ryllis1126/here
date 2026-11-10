/* Boot regression: .data survives warm restart while .bss is reinitialized. */
#include "io.h"
#include "power.h"
#include <stdint.h>

static volatile uint64_t round_number = 1; /* .data, must not be cleared */
static volatile uint64_t uninitialized;  /* .bss, must be cleared */

int main(void) {
    if (round_number == 1) {
        round_number = 2;
        uninitialized = 0xdeadbeef12345678ull;
        __asm__ volatile ("j _start" ::: "memory");
        __builtin_unreachable();
    }
    if (round_number == 2 && uninitialized == 0) {
        printf("STARTUP BSS PASS: .data retained, .bss cleared\n");
    } else {
        printf("STARTUP BSS FAIL\n");
    }
    PowerOff();
    return 0;
}
