/* A portable terminal calculator, with stdio (host) and HERE UART adapters. */
#include <stdint.h>
#ifdef HOST_TEST
#include <stdio.h>
static int read_char(void) { return getchar(); }
#else
#include "io.h"
#include "power.h"
static int read_char(void) { return uart_getc(); }
#endif

static int equal(const char *a, const char *b) {
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}

static int space(char c) { return c == ' ' || c == '\t' || c == '\r'; }

/* Return 0 at EOF, 1 for a complete line, -1 for an overlong drained line. */
static int read_line(char *line, unsigned capacity) {
    unsigned used = 0;
    int too_long = 0;
    int c;
    while ((c = read_char()) >= 0 && c != '\n') {
        if (used + 1 < capacity) line[used++] = (char)c;
        else too_long = 1;
    }
    line[used] = 0;
    if (c < 0 && used == 0) return 0;
    return too_long ? -1 : 1;
}

static int integer(const char *s, int32_t *out) {
    int negative = *s == '-';
    if (*s == '-' || *s == '+') ++s;
    if (!*s) return 0;
    uint64_t value = 0;
    uint64_t limit = negative ? 2147483648ull : 2147483647ull;
    for (; *s; ++s) {
        if (*s < '0' || *s > '9') return 0;
        unsigned digit = (unsigned)(*s - '0');
        if (value > (limit - digit) / 10) return 0;
        value = value * 10 + digit;
    }
    *out = (int32_t)(negative ? -(int64_t)value : (int64_t)value);
    return 1;
}

static int command(char *line) {
    char *tokens[4];
    unsigned count = 0;
    while (*line) {
        while (space(*line)) ++line;
        if (!*line) break;
        if (count == 4) { printf("ERROR syntax\n"); return 1; }
        tokens[count++] = line;
        while (*line && !space(*line)) ++line;
        if (*line) *line++ = 0;
    }
    if (!count) return 1;
    if (count == 1 && equal(tokens[0], "quit")) return 0;
    if (count == 1 && equal(tokens[0], "help")) {
        printf("COMMANDS: add sub mul div; help; quit\n");
        return 1;
    }
    int32_t a, b;
    if (count != 3 || !integer(tokens[1], &a) || !integer(tokens[2], &b)) {
        printf("ERROR syntax\n"); return 1;
    }
    int64_t result;
    if (equal(tokens[0], "add")) result = (int64_t)a + b;
    else if (equal(tokens[0], "sub")) result = (int64_t)a - b;
    else if (equal(tokens[0], "mul")) result = (int64_t)a * b;
    else if (equal(tokens[0], "div")) {
        if (b == 0) { printf("ERROR division by zero\n"); return 1; }
        result = (int64_t)a / b;
    } else { printf("ERROR syntax\n"); return 1; }
    if (result < -2147483648ll || result > 2147483647ll) {
        printf("ERROR overflow\n"); return 1;
    }
    printf("RESULT %d\n", (int)result);
    return 1;
}

int main(void) {
#ifdef HOST_TEST
    setvbuf(stdout, NULL, _IONBF, 0);
#endif
    char line[96];
    printf("CALCULATOR READY\n");
    for (;;) {
        int status = read_line(line, sizeof(line));
        if (status == 0) break;
        if (status < 0) { printf("ERROR input too long\n"); continue; }
        if (!command(line)) break;
    }
    printf("CALCULATOR BYE\n");
#ifndef HOST_TEST
    PowerOff();
#endif
    return 0;
}
