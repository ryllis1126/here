#include <stddef.h>
#include <stdint.h>

void lab_axpy(uint32_t *restrict out, const uint32_t *restrict x,
              const uint32_t *restrict y, uint32_t a, size_t n) {
    for (size_t i = 0; i < n; ++i)
        out[i] = a * x[i] + y[i];
}
