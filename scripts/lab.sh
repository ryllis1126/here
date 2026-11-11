#!/usr/bin/env bash
set -euo pipefail
LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$LAB_ROOT"
mkdir -p .cache/lab
export PATH="/opt/riscv/bin:$PATH"
LAB_JOBS=${LAB_JOBS:-4}
LAB_TIMEOUT=${LAB_TIMEOUT:-60}
LAB_CYCLES=${LAB_CYCLES:-10000000}
LAB_TEST_TIMEOUT=${LAB_TEST_TIMEOUT:-300}
lab_log() {
    local name=$1
    shift
    local logfile=".cache/lab/${name}-$(date -u +%Y%m%dT%H%M%S)-$$.log"
    {
        printf 'LOG=%s\nCOMMAND:' "$logfile"
        printf ' %q' "$@"
        printf '\n'
    } | tee "$logfile"
    local result=0
    "$@" 2>&1 | tee -a "$logfile" || result=$?
    printf 'EXIT_CODE=%s\n' "$result" | tee -a "$logfile"
    return "$result"
}
case "${1:-help}" in
    env)
        failed=0
        for tool in rustc cargo make autoconf python3 riscv64-unknown-elf-gcc riscv64-unknown-elf-objdump; do
            if command -v "$tool" >/dev/null; then
                printf '%s: %s\n' "$tool" "$(command -v "$tool")"
            else
                printf 'MISSING: %s\n' "$tool"; failed=1
            fi
        done
        rustc --version
        cargo --version
        riscv64-unknown-elf-gcc --version | head -n 1
        if ! bash "$LAB_ROOT/scripts/lab.sh" gdb --version; then failed=1; fi
        if [[ ! -f riscv-tests/isa/rv64ui-p-add ]]; then
            printf 'MISSING: riscv-tests ISA ELF; run bash scripts/lab.sh isa\n'; failed=1
        fi
        git status --short --branch
        exit "$failed"
        ;;
    build)
        shift
        lab_log cargo-build cargo build --release --locked -j "$LAB_JOBS" "$@"
        lab_log baremetal-build make -C test_resources -j "$LAB_JOBS"
        ;;
    isa)
        shift
        # The integration suite consumes these eight RV64 groups, both p/v variants.
        # Build directly using the checked-in Makefile; no configure rewrite/install.
        lab_log isa-build make -C riscv-tests/isa -j "$LAB_JOBS" \
            rv64ui rv64uc rv64um rv64ua rv64uf rv64ud rv64si rv64mi "$@"
        test -f riscv-tests/isa/rv64ui-p-add
        ;;
    test)
        shift
        lab_log cargo-test timeout --kill-after=5 "$LAB_TEST_TIMEOUT" cargo test --locked --features riscv-tests -j "$LAB_JOBS" "$@"
        ;;
    run)
        shift
        if [[ $# -eq 0 ]]; then printf 'usage: bash scripts/lab.sh run ELF [HERE args]\n' >&2; exit 2; fi
        if [[ ! -x target/release/here ]]; then printf 'Build first: bash scripts/lab.sh build\n' >&2; exit 2; fi
        lab_log emulator timeout --foreground "$LAB_TIMEOUT" target/release/here "$@" --max-cycles "$LAB_CYCLES"
        ;;
    gdb)
        shift
        if [[ -d .cache/tools/libpython/usr/lib/x86_64-linux-gnu ]]; then
            export LD_LIBRARY_PATH="$LAB_ROOT/.cache/tools/libpython/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
            export PYTHONHOME="$LAB_ROOT/.cache/tools/libpython/usr"
        fi
        exec riscv64-unknown-elf-gdb "$@"
        ;;
    dtc)
        shift
        if command -v dtc >/dev/null; then exec dtc "$@"; fi
        if [[ ! -x .cache/tools/dtc/usr/bin/dtc ]]; then
            printf 'Prepare first: bash scripts/setup-linux.sh\n' >&2; exit 2
        fi
        export LD_LIBRARY_PATH="$LAB_ROOT/.cache/tools/dtc/usr/lib/x86_64-linux-gnu:$LAB_ROOT/.cache/tools/dtc/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
        exec .cache/tools/dtc/usr/bin/dtc "$@"
        ;;
    linux-prepare)
        shift
        bash scripts/setup-linux.sh alpine
        lab_log linux-prepare python3 scripts/prepare-linux.py "$@"
        ;;
    help) printf 'usage: bash scripts/lab.sh {env|build|isa|test|run ELF|gdb|dtc|linux-prepare} [args]\n' ;;
    *) printf 'unknown lab command: %s\n' "$1" >&2; exit 2 ;;
esac
