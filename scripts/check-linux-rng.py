#!/usr/bin/env python3
"""Boot the course Linux image and read the native virtio_rng device."""
import importlib
import os
from pathlib import Path
import selectors
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
tools = importlib.import_module("check-debuggers")
command = ["target/release/here", ".cache/images/linux-busybox-rv64gc.bin",
           "--dtb", "dts/virt.dtb", "--device", "virtio-rng:/dev/urandom",
           "--max-cycles", "12000000000"]
path = tools.EVIDENCE / "ch5-linux-rng.txt"
header = f"COMMAND: {command!r}\nHOST_TIMEOUT=200s\n"
output = bytearray()
process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
activated = sent = False
status = "RUNNING"
try:
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + 200
        while True:
            if time.monotonic() >= deadline:
                status = "TIMEOUT"
                raise TimeoutError("Linux RNG verification exceeded 200 seconds")
            if not selector.select(0.1):
                continue
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                break
            output.extend(chunk)
            text = output.decode(errors="replace")
            if not activated and "Please press Enter to activate this console." in text:
                process.stdin.write(b"\n")
                process.stdin.flush()
                activated = True
            if not sent and ("/ # " in text or "~ # " in text):
                # Keep each operation's result, and print PASS only on success.
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
                process.stdin.write(script.encode())
                process.stdin.flush()
                sent = True
        process.wait(timeout=max(1, deadline - time.monotonic()))
    status = "EXITED"
finally:
    if process.poll() is None:
        process.kill()
    rest, _ = process.communicate(timeout=5)
    output.extend(rest)
    text = output.decode(errors="replace")
    tools.save(path, header + text + f"\nSTATUS={status}\nEXIT_CODE={process.returncode}\n")

assert process.returncode == 0 and sent, text[-6000:]
assert "READ_STATUS=0" in text and "32 /tmp/entropy" in text, text[-6000:]
assert "virtio_rng.0" in text, text[-6000:]
# Match a result line, never the shell's echo of a command containing PASS.
assert any(line.strip().startswith("HERE_RNG_PASS") for line in text.splitlines()), text[-6000:]
assert "Max cycles reached" not in text and "Kernel panic" not in text, text[-6000:]
print("Linux: native virtio_rng.0, /dev/hwrng and actual 32-byte read verified")
