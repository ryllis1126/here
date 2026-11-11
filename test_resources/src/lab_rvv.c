#include "io.h"
#include "power.h"
#include "rvv_test.h"

uint32_t lab_dot(const uint32_t *a, const uint32_t *b, size_t n);
void lab_gemm(uint32_t *c, const uint32_t *a, const uint32_t *b,
              size_t m, size_t n, size_t k);
void lab_axpy(uint32_t *restrict out, const uint32_t *restrict x,
              const uint32_t *restrict y, uint32_t a, size_t n);

static uint32_t state = 0xcafe125u;
static uint32_t sample(void) {
    state = state * 1664525u + 1013904223u;
    return state;
}

static int mismatch(const char *kernel, size_t index) {
    printf("LAB RVV FAIL %s index=%d\n", kernel, (int)index);
    fail();
    return 1;
}

static uint32_t x[257], y[257], z[258];

static int check_vectors(void) {
    static const size_t lengths[] = {0, 1, 2, 3, 4, 5, 7, 8, 9, 31, 32, 33, 129, 257};
    for (size_t i = 0; i < 257; ++i) {
        x[i] = sample();
        y[i] = sample();
    }
    x[0] = UINT32_MAX;
    y[0] = 0x80000000u;
    x[1] = 0;
    y[1] = UINT32_MAX;
    for (size_t t = 0; t < sizeof(lengths) / sizeof(lengths[0]); ++t) {
        size_t n = lengths[t];
        uint32_t expected = 0;
        for (size_t i = 0; i < n; ++i)
            expected += x[i] * y[i];
        if (lab_dot(x, y, n) != expected)
            return mismatch("dot", n);
        const uint32_t factor = 0xffffffedu;
        for (size_t i = 0; i < 258; ++i)
            z[i] = 0xdeadbeefu;
        lab_axpy(z + 1, x, y, factor, n);
        for (size_t i = 0; i < n; ++i)
            if (z[i + 1] != factor * x[i] + y[i])
                return mismatch("compiler-axpy", i);
        if (z[0] != 0xdeadbeefu)
            return mismatch("axpy-head", n);
        for (size_t i = n + 1; i < 258; ++i)
            if (z[i] != 0xdeadbeefu)
                return mismatch("axpy-tail", i);
    }
    printf("RVV DOT PASS: 14 lengths\n");
    printf("RVV COMPILER AXPY PASS: 14 lengths\n");
    return 0;
}

static int check_matrices(void) {
    static const size_t sizes[][3] = {
        {2, 2, 2}, {4, 4, 4}, {3, 5, 7}, {4, 19, 13},
        {2, 9, 0}, {0, 5, 7}, {2, 0, 7},
    };
    uint32_t a[4 * 13], b[13 * 19], c[4 * 19 + 2];
    for (size_t i = 0; i < 4 * 13; ++i)
        a[i] = sample();
    for (size_t i = 0; i < 13 * 19; ++i)
        b[i] = sample();
    for (size_t t = 0; t < sizeof(sizes) / sizeof(sizes[0]); ++t) {
        const size_t m = sizes[t][0], n = sizes[t][1], k = sizes[t][2];
        for (size_t i = 0; i < 4 * 19 + 2; ++i)
            c[i] = 0xdeadbeefu;
        lab_gemm(c + 1, a, b, m, n, k);
        for (size_t row = 0; row < m; ++row) {
            for (size_t col = 0; col < n; ++col) {
                uint32_t expected = 0;
                for (size_t p = 0; p < k; ++p)
                    expected += a[row * k + p] * b[p * n + col];
                const size_t i = row * n + col;
                if (c[i + 1] != expected)
                    return mismatch("gemm", i);
            }
        }
        if (c[0] != 0xdeadbeefu)
            return mismatch("gemm-head", t);
        for (size_t i = m * n + 1; i < 4 * 19 + 2; ++i)
            if (c[i] != 0xdeadbeefu)
                return mismatch("gemm-tail", i);
    }
    printf("RVV GEMM PASS: 7 shapes\n");
    return 0;
}

int main(void) {
    rvv_enable();
    if (check_vectors() || check_matrices())
        return 1;
    printf("LAB RVV PASS\n");
    pass();
    return 0;
}
