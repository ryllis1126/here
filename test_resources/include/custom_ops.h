#ifndef HERE_LAB_CUSTOM_OPS_H
#define HERE_LAB_CUSTOM_OPS_H
#include <stdint.h>

/* RV64 custom-0: eight independent unsigned byte lanes, no memory effects.
 * psub8 wraps each lane modulo 256; pabsdiff8 returns each unsigned distance.
 */
static inline uint64_t lab_psub8(uint64_t a, uint64_t b) {
    uint64_t result;
    __asm__ volatile (".insn r 0x0b, 2, 0, %0, %1, %2"
                      : "=r"(result) : "r"(a), "r"(b));
    return result;
}

static inline uint64_t lab_pabsdiff8(uint64_t a, uint64_t b) {
    uint64_t result;
    __asm__ volatile (".insn r 0x0b, 3, 0, %0, %1, %2"
                      : "=r"(result) : "r"(a), "r"(b));
    return result;
}
#endif
