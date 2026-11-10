#!/usr/bin/env python3
"""Validate real guest monitor assertions and its scheduling/trap evidence."""
import importlib
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
tools = importlib.import_module("check-debuggers")
PREFIX = os.environ.get("HERE_LAB_CHAPTER", "ch4")
assert Path("test_resources/src/lab_monitor.c").exists(), "M-mode monitor not implemented yet"
command = ["target/release/here", "test_resources/bin/lab_monitor.elf",
           "--max-cycles", "20000000"]
result = tools.capture(command, f"{PREFIX}-monitor.txt", 30)
output = result.stdout + result.stderr
assert result.returncode == 0, output
assert "MONITOR FAIL" not in output, output
assert "Max cycles reached" not in output, output
for marker in ("MONITOR PASS", "CSR ECALL PASS", "CSR ILLEGAL SKIP PASS",
               "CSR ILLEGAL KILL PASS", "PREEMPT PRIORITY PASS", "ROUND ROBIN PASS",
               "SLEEP IDLE PASS", "CONTEXT TP PASS", "SPAWN EXIT PASS"):
    assert marker in output, f"missing {marker}:\n{output}"
symbols = subprocess.check_output(
    ["/opt/riscv/bin/riscv64-unknown-elf-nm", "-n", "test_resources/bin/lab_monitor.elf"],
    text=True, timeout=10)
addresses = {parts[2]: int(parts[0], 16) for line in symbols.splitlines()
             if len(parts := line.split()) == 3}
illegal = re.findall(r"ILLEGAL cause=(0x[0-9a-f]+) pc=(0x[0-9a-f]+) tval=(0x[0-9a-f]+)", output)
assert [(int(c, 16), int(pc, 16), int(t, 16)) for c, pc, t in illegal] == [
    (2, addresses["lab_fault_skip"], 0xfff00073),
    (2, addresses["lab_fault_kill"], 0x30002573)], illegal
assert re.search(r"ECALL cause=0x8 pc=0x[0-9a-f]+ tval=0x0 MPP=0", output)
trace = [(int(a), int(b), reason, int(priority)) for a, b, reason, priority in re.findall(
    r"SWITCH from=(\d+) to=(\d+) reason=(timer|trap) priority=(-?\d+)", output)]
assert (0, 2, "trap", 2) in trace, "spawn did not immediately preempt the low-priority task"
assert any(a in (0, 1) and b == 2 and why == "timer" for a, b, why, _ in trace)
assert {(0, 1), (1, 0)} <= {(a, b) for a, b, why, p in trace if why == "timer" and p == 1}
assert any(b == 4 for _, b, _, _ in trace) and any(a == 4 and why == "timer" for a, _, why, _ in trace)
fair = re.search(r"ROUND ROBIN PASS ticks0=(\d+) ticks1=(\d+) switches=(\d+)", output)
assert fair and all(int(value) >= 2 for value in fair.groups())
for target in ("ecall_test", "trap_test", "clint"):
    cmd = ["target/release/here", f"test_resources/bin/{target}.elf", "--max-cycles", "1000000"]
    regression = tools.capture(cmd, f"{PREFIX}-regression-{target}.txt", 15)
    assert regression.returncode == 0, regression.stderr
    assert "PASS" in regression.stdout and "FAIL" not in regression.stdout, regression.stdout
    assert "Max cycles reached" not in regression.stderr, regression.stderr
print("monitor: U/M traps, CSR recovery, context, timer fairness, priority, sleep/spawn/exit passed")
