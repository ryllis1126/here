#!/usr/bin/env python3
"""Boot the course Linux image and read the native virtio_rng device."""
import importlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
session = importlib.import_module("linux-session")
prefix = os.environ.get("HERE_LAB_CHAPTER", "ch5")
command = ["target/release/here", ".cache/images/linux-busybox-rv64gc.bin",
           "--dtb", "dts/virt.dtb", "--device", "virtio-rng:/dev/urandom",
           "--max-cycles", "12000000000"]
script = (
    "echo HERE_RNG_BEGIN\n"
    "cat /sys/class/misc/hw_random/rng_current\n"
    "cat /sys/class/misc/hw_random/dev\n"
    "mdev -s; echo MDEV_STATUS=$?\n"
    "ls -l /dev/hwrng\n"
    "dd if=/dev/hwrng of=/tmp/entropy bs=32 count=1; echo READ_STATUS=$?\n"
    "wc -c /tmp/entropy\n"
    "od -An -tx1 /tmp/entropy\n"
    "test -c /dev/hwrng && test $(wc -c < /tmp/entropy) -eq 32 && echo HERE_RNG_PASS\n"
    "poweroff -f\n"
)

text = session.run(command, f"{prefix}-linux-rng.txt", script, host_timeout=200)
for expected in ("MDEV_STATUS=0", "READ_STATUS=0", "32 /tmp/entropy", "virtio_rng.0", "HERE_RNG_PASS"):
    assert session.result_line(text, expected), f"missing {expected}:\n{text[-6000:]}"
print("Linux: native virtio_rng.0, /dev/hwrng and actual 32-byte read verified")
