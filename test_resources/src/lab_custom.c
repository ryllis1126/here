#include "custom_ops.h"
#include "io.h"

/* Independent scalar reference: shifts/masks, rather than Rust byte arrays. */
static uint64_t reference(uint64_t a, uint64_t b, int absolute) {
    uint64_t result = 0;
    for (unsigned lane = 0; lane < 8; ++lane) {
        unsigned x = (unsigned)((a >> (lane * 8)) & 255);
        unsigned y = (unsigned)((b >> (lane * 8)) & 255);
        unsigned value = absolute ? (x >= y ? x - y : y - x) : x - y;
        result |= (uint64_t)(value & 255) << (lane * 8);
    }
    return result;
}

static int check(uint64_t a, uint64_t b) {
    uint64_t actual[2] = {lab_psub8(a, b), lab_pabsdiff8(a, b)};
    for (int op = 0; op < 2; ++op) {
        uint64_t expected = reference(a, b, op);
        if (actual[op] != expected) {
            printf("CUSTOM BACKEND FAIL op=%d a=%llx b=%llx got=%llx expected=%llx\n",
                   op, (unsigned long long)a, (unsigned long long)b,
                   (unsigned long long)actual[op], (unsigned long long)expected);
            PowerOff();
            return 0;
        }
    }
    return 1;
}

static uint64_t random_word(uint64_t *seed) {
    *seed ^= *seed << 13;
    *seed ^= *seed >> 7;
    *seed ^= *seed << 17;
    return *seed;
}

int main(void) {
    static const uint64_t cases[][2] = {
        {0, 0}, {UINT64_MAX, UINT64_MAX}, {UINT64_MAX, 0x0101010101010101ull},
        {0, 0x0101010101010101ull},
        {0x8080808080808080ull, 0x7f7f7f7f7f7f7f7full},
        {0x0001000100010001ull, 0x0100010001000100ull},
        {0x0011223344556677ull, 0x7766554433221100ull},
        {0x0100000000000000ull, 0},
    };
    int count = 0;
    for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        if (!check(cases[i][0], cases[i][1])) return 1;
        count += 2;
    }
    for (unsigned lane = 0; lane < 8; ++lane) {
        if (!check(0, 1ull << (lane * 8))) return 1;
        count += 2;
    }
    uint64_t seed = 0x9e3779b97f4a7c15ull;
    for (unsigned i = 0; i < 512; ++i) {
        uint64_t a = random_word(&seed);
        uint64_t b = random_word(&seed);
        if (!check(a, b)) return 1;
        count += 2;
    }
    printf("CUSTOM BACKEND PASS: %d checks\n", count);
    pass();
    return 0;
}
