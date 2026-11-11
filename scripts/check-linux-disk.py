#!/usr/bin/env python3
"""Verify Ext4 DMA I/O and the personal Linux calculator in actual HERE Linux."""
import importlib
import os
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
session = importlib.import_module("linux-session")
prefix = os.environ.get("HERE_LAB_CHAPTER", "ch6")
image = importlib.import_module("lab-image").existing_image(
    os.environ.get("HERE_BUSYBOX_IMAGE", "busybox-lab.img"))
marker = f"HERE_EXT4_{uuid.uuid4().hex}"
command = ["target/release/here", ".cache/images/linux-busybox-rv64gc.bin",
           "--dtb", "dts/linux-lab.dtb", "--device", f"virtio-block:{image}",
           "--device", "virtio-rng:/dev/urandom", "--max-cycles", "16000000000"]
commands = (
    "mdev -s\n"
    "mkdir -p /mnt\n"
    "mount -t ext4 /dev/vda /mnt; echo MOUNT_STATUS=$?\n"
    "cat /proc/mounts\n"
    "printf 'add 40 2\\nsub -2 3\\nmul 7 -8\\ndiv -7 2\\nadd 2147483647 1\\ndiv 3 0\\nquit\\n' | /mnt/calculator; echo APP_STATUS=$?\n"
    f"echo {marker} > /mnt/persistent.txt; echo WRITE_STATUS=$?\n"
    "sync\n"
    "umount /mnt; echo UMOUNT_STATUS=$?\n"
    "poweroff -f\n"
)
text = session.run(command, f"{prefix}-linux-disk.txt", commands, host_timeout=240)
for expected in ("MOUNT_STATUS=0", "APP_STATUS=0", "WRITE_STATUS=0", "UMOUNT_STATUS=0", "CALCULATOR READY",
                 "RESULT 42", "RESULT -5", "RESULT -56", "RESULT -3", "ERROR overflow",
                 "ERROR division by zero", "CALCULATOR BYE"):
    assert session.result_line(text, expected), f"missing {expected}:\n{text[-6000:]}"
assert "/dev/vda /mnt ext4 rw" in text, text[-6000:]
tools = importlib.import_module("check-debuggers")
result = tools.capture(["debugfs", "-R", "cat /persistent.txt", image],
                       f"{prefix}-disk-persistence.txt", 15)
assert result.returncode == 0 and result.stdout.strip() == marker, result.stderr
check = tools.capture(["e2fsck", "-fn", image], f"{prefix}-e2fsck.txt", 30)
assert check.returncode == 0, check.stdout + check.stderr
print("Linux Ext4: calculator 6 cases, clean unmount, persistent bytes and e2fsck verified")
