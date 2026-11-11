#!/usr/bin/env python3
"""Verify the integer RVV guests and inspect the compiler-generated kernel."""
import importlib
from pathlib import Path
import os
import re

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
tools = importlib.import_module("check-debuggers")
objdump = "/opt/riscv/bin/riscv64-unknown-elf-objdump"
guest = "test_resources/bin/lab_rvv.elf"

for kernel, instructions in (
    ("lab_dot", {"vsetvli", "vle32.v", "vmacc.vv", "vslidedown.vx", "vadd.vv", "vmv.x.s"}),
    ("lab_gemm", {"vsetvli", "vle32.v", "vmacc.vx", "vse32.v"}),
    ("lab_axpy", {"vsetvli", "vle32.v", "vmacc.vx", "vse32.v"}),
):
    result = tools.capture([objdump, "-d", f"--disassemble={kernel}", guest],
                           f"ch7-{kernel}.txt", 15)
    assert result.returncode == 0, result.stderr
    actual = set(re.findall(r"^\s*[\da-f]+:\s+[\da-f]+\s+(\S+)", result.stdout, re.M))
    assert instructions <= actual, (kernel, instructions - actual)
    assert not any(op.startswith("vf") for op in actual), (kernel, actual)

scalar = ".cache/lab/lab_rvv_scalar.o"
result = tools.capture(["clang", "--target=riscv64-unknown-elf", "-march=rv64imfdvzicsr",
                        "-mabi=lp64d", "-O3", "-ffreestanding", "-fno-vectorize",
                        "-fno-slp-vectorize", "-c", "test_resources/src/lab_rvv_auto.c",
                        "-o", scalar], "ch7-scalar-build.txt", 30)
assert result.returncode == 0, result.stderr
result = tools.capture([objdump, "-d", scalar], "ch7-scalar-disassembly.txt", 15)
assert result.returncode == 0 and not re.search(
    r"^\s*[\da-f]+:\s+[\da-f]+\s+v\w", result.stdout, re.M), result.stdout

for program, filename, required in (
    (guest, "ch7-rvv-uart.txt", {"LAB RVV PASS", "RVV DOT PASS: 14 lengths",
                                "RVV COMPILER AXPY PASS: 14 lengths", "RVV GEMM PASS: 7 shapes"}),
    ("test_resources/bin/vector_kernels.elf", "ch7-upstream-vector-uart.txt", {"vector kernels ok"}),
):
    result = tools.capture(["target/release/here", program, "--isa", "RV64GCV",
                            "--max-cycles", "5000000"], filename, 60)
    assert result.returncode == 0, result.stderr
    assert required <= {line.strip() for line in result.stdout.splitlines()}, result.stdout
    assert "FAIL" not in result.stdout and "Max cycles reached" not in result.stdout + result.stderr

print("Integer RVV verified: dot and compiler AXPY at 14 lengths, GEMM at 7 shapes, and original vector kernels")
