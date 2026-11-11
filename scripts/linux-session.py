#!/usr/bin/env python3
"""Bounded serial Linux session shared by experiment checks."""
import importlib
import os
import selectors
import subprocess
import time


def run(command, evidence_name, commands, host_timeout=200, after_ready=None):
    tools = importlib.import_module("check-debuggers")
    output = bytearray()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    activated = sent = False
    ready_sent = after_ready is None
    status = "RUNNING"
    header = f"COMMAND: {command!r}\nHOST_TIMEOUT={host_timeout}s\n"
    path = tools.EVIDENCE / evidence_name
    tools.save(path, header + "STATUS=RUNNING\n")
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + host_timeout
            while True:
                if time.monotonic() >= deadline:
                    status = "TIMEOUT"
                    raise TimeoutError(f"Linux session exceeded {host_timeout}s")
                if not selector.select(0.1):
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    break
                output.extend(chunk)
                text = output.decode(errors="replace")
                tools.save(path, header + text + "\nSTATUS=RUNNING\n")
                if "Kernel panic" in text:
                    status = "KERNEL_PANIC"
                    raise RuntimeError(text[-6000:])
                if not activated and "Please press Enter to activate this console." in text:
                    process.stdin.write(b"\n")
                    process.stdin.flush()
                    activated = True
                if not sent and ("/ # " in text or "~ # " in text):
                    process.stdin.write(commands.encode())
                    process.stdin.flush()
                    sent = True
                if sent and not ready_sent and after_ready[0] in text:
                    process.stdin.write(after_ready[1].encode())
                    process.stdin.flush()
                    ready_sent = True
            process.wait(timeout=max(1, deadline - time.monotonic()))
        status = "EXITED"
    finally:
        if process.poll() is None:
            process.kill()
        rest, _ = process.communicate(timeout=5)
        output.extend(rest)
        text = output.decode(errors="replace")
        tools.save(tools.EVIDENCE / evidence_name,
                   header + text + f"\nSTATUS={status}\nEXIT_CODE={process.returncode}\n")
    assert process.returncode == 0 and sent and ready_sent, text[-6000:]
    assert "Max cycles reached" not in text and "Kernel panic" not in text, text[-6000:]
    return text


def result_line(text, expected):
    """Avoid treating the shell echo of an assertion command as its result."""
    return any(line.strip() == expected for line in text.splitlines())
