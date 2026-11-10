#!/usr/bin/env python3
"""Check the same calculator on the host and through HERE's real UART."""
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "scripts"))
from importlib import import_module
debug_tools = import_module("check-debuggers")
save = debug_tools.save
capture = debug_tools.capture
EVIDENCE = debug_tools.EVIDENCE

CASES = [
    ("help", "COMMANDS: add sub mul div; help; quit"),
    ("add 2 3", "RESULT 5"),
    ("mul -7 6", "RESULT -42"),
    ("div -7 3", "RESULT -2"),
    ("sub -2147483648 0", "RESULT -2147483648"),
    ("add 2147483647 1", "ERROR overflow"),
    ("sub -2147483648 1", "ERROR overflow"),
    ("mul 2147483647 2147483647", "ERROR overflow"),
    ("div -2147483648 -1", "ERROR overflow"),
    ("div 1 0", "ERROR division by zero"),
    ("add 2147483648 0", "ERROR syntax"),
    ("add 1", "ERROR syntax"),
    ("add 1 2 trailing", "ERROR syntax"),
    ("unknown 1 2", "ERROR syntax"),
    ("x" * 160, "ERROR input too long"),
    ("add 40 2", "RESULT 42"),
]


def host_test():
    source = ROOT / "test_resources/src/lab_calculator.c"
    assert source.exists(), "calculator not implemented yet"
    target = ROOT / ".cache/lab/calculator-host"
    command = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2",
               "-fsanitize=undefined", "-DHOST_TEST", str(source), "-o", str(target)]
    result = capture(command, "ch1-host-build.txt", 30)
    assert result.returncode == 0, result.stderr
    data = "\n".join(command for command, _ in CASES) + "\nquit\n"
    result = capture([str(target)], "ch1-host.txt", 10, input=data)
    assert result.returncode == 0 and not result.stderr, result.stderr
    actual = [line.strip() for line in result.stdout.splitlines()
              if line.startswith(("RESULT", "ERROR", "COMMANDS"))]
    assert actual == [expected for _, expected in CASES], actual
    assert "CALCULATOR BYE" in result.stdout
    print(f"host calculator: {len(CASES)} cases passed with UBSan")


def startup_test():
    result = capture(["target/release/here", "test_resources/bin/lab_startup.elf",
                      "--max-cycles", "200000"], "ch1-startup.txt", 15,
                     stdin=subprocess.DEVNULL)
    assert result.returncode == 0, result.stderr
    assert "STARTUP BSS PASS" in result.stdout, result.stdout
    assert "STARTUP BSS FAIL" not in result.stdout
    print("startup: warm-restart .bss clearing and .data preservation passed")


def guest_test():
    command = ["target/release/here", "test_resources/bin/lab_calculator.elf",
               "--max-cycles", "1000000000"]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
    transcript = bytearray()
    path = EVIDENCE / "ch1-calculator-uart.txt"
    save(path, f"COMMAND: {command!r}\nSTATUS=RUNNING")
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)

            def await_text(expected, start=0):
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if expected.encode() in transcript[start:]:
                        return
                    if process.poll() is not None:
                        break
                    if selector.select(0.05):
                        transcript.extend(os.read(process.stdout.fileno(), 65536))
                raise AssertionError(f"UART missing {expected!r}: {transcript.decode(errors='replace')}")

            await_text("CALCULATOR READY")
            for line, expected in CASES:
                begin = len(transcript)
                process.stdin.write((line + "\n").encode())
                process.stdin.flush()
                await_text(expected, begin)
            process.stdin.write(b"quit\n")
            process.stdin.flush()
            await_text("CALCULATOR BYE")
        output, _ = process.communicate(timeout=10)
        transcript.extend(output)
        assert process.returncode == 0, process.returncode
        assert b"Max cycles reached" not in transcript
        print(f"HERE UART calculator: {len(CASES)} cases and graceful exit passed")
    finally:
        if process.poll() is None:
            process.kill()
            output, _ = process.communicate()
            transcript.extend(output)
        save(path, f"COMMAND: {command!r}\n{transcript.decode(errors='replace')}\nEXIT_CODE={process.returncode}")


if __name__ == "__main__":
    if "--startup-only" in sys.argv:
        startup_test()
    else:
        host_test()
        startup_test()
        guest_test()
