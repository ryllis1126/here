#include "custom_ops.h"
#include "io.h"

int main(void) {
    uint64_t a = 0x0102030405060708ull;
    uint64_t b = 0x0807060504030201ull;
    (void)lab_psub8(a, b);
    (void)lab_pabsdiff8(a, b);
    printf("CUSTOM FRONTEND PASS: PSUB8 and PABSDIFF8 dispatched; arithmetic deferred\n");
    pass();
    return 0;
}
