#!/usr/bin/env python3
"""Run the custom-instruction guest and inspect a fresh, isolated execution log."""
import importlib
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
tools = importlib.import_module("check-debuggers")
run_dir = ROOT / ".cache/lab" / f"custom-{time.time_ns()}"
run_dir.mkdir(parents=True)
command = [str(ROOT / "target/release/here"),
           str(ROOT / "test_resources/bin/lab_custom.elf"),
           "--max-cycles", "1000000", "--loglevel", "info"]
result = tools.capture(command, "ch2-custom-uart.txt", 20, cwd=run_dir)
assert result.returncode == 0, result.stderr
assert "CUSTOM FRONTEND PASS" in result.stdout, result.stdout
assert "Max cycles reached" not in result.stderr, result.stderr
logs = list((run_dir / "logs").glob("*.log"))
assert logs, "no execution logs generated"
content = "\n".join(path.read_text() for path in logs)
for instruction in ("PSUB8", "PABSDIFF8"):
    expected = f"[LabCustom] {instruction} phase=frontend rd="
    assert content.count(expected) == 1, content
tools.save(tools.EVIDENCE / "ch2-custom-execution.txt",
           f"COMMAND: {command!r}\nCWD: {run_dir}\n{content}\nEXIT_CODE={result.returncode}")
print("custom frontend: both C APIs dispatched once; execution logs verified")
