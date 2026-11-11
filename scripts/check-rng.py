#!/usr/bin/env python3
"""Validate actual MMIO DMA and PLIC interrupts with the bare-metal driver."""
import importlib
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
tools = importlib.import_module("check-debuggers")
PREFIX = os.environ.get("HERE_LAB_CHAPTER", "ch5")
command = ["target/release/here", "test_resources/bin/lab_rng.elf",
           "--device", "virtio-rng:/dev/urandom", "--max-cycles", "50000000"]
result = tools.capture(command, f"{PREFIX}-rng-baremetal.txt", 30)
output = result.stdout + result.stderr
assert result.returncode == 0, output
assert "RNG IRQ DMA PASS: requests=2 bytes=128 irq=2" in output, output
assert "RNG FAIL" not in output and "Max cycles reached" not in output, output
print("VirtIO-RNG: two fresh DMA buffers, two PLIC IRQs and reset verified")
