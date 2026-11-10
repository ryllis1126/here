#!/usr/bin/env python3
"""Exercise real rvdb and GDB Remote sessions, retaining complete transcripts."""
import os
from pathlib import Path
import selectors
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
EVIDENCE = ROOT / "docs/experiment/evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)
ELF = "test_resources/bin/main.elf"
PREFIX = os.environ.get("HERE_LAB_CHAPTER", "ch0")


def save(path, text):
    # Preserve output content while normalizing terminal line endings/whitespace.
    path.write_text("\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n")


def capture(command, evidence_name, timeout, **kwargs):
    path = EVIDENCE / evidence_name
    header = f"COMMAND: {command!r}\n"
    save(path, header + "STATUS=RUNNING\n")
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired as error:
        def decoded(value):
            return value.decode(errors="replace") if isinstance(value, bytes) else value or ""
        save(path, header + decoded(error.stdout) + decoded(error.stderr)
             + f"\nSTATUS=TIMEOUT after {timeout}s\n")
        raise
    save(path, header + result.stdout + result.stderr
         + f"\nEXIT_CODE={result.returncode}\n")
    return result


def run_rvdb():
    command = ["target/release/here", ELF, "-g", "-S", "scripts/ch0.rvdb"]
    result = capture(command, f"{PREFIX}-rvdb.txt", 20, stdin=subprocess.DEVNULL)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    for expected in ("pc = 0x80000000", "pc = 0x80000004", "Breakpoint set",
                     "Breakpoint hit", "Breakpoint removed", "sp", "80000000"):
        assert expected in output, f"rvdb missing {expected!r}:\n{output}"
    assert "error:" not in output.lower(), output
    print("rvdb: registers, memory, disassembly, step and breakpoint verified")


def run_gdb():
    # The documented port is intentional; fail rather than disturbing another service.
    server_command = ["target/release/here", ELF, "-G"]
    server = subprocess.Popen(server_command, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, bufsize=1)
    transcript = []
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(server.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    raise RuntimeError("GDB server exited: " + "".join(transcript) + server.stdout.read())
                if not selector.select(0.1):
                    continue
                chunk = os.read(server.stdout.fileno(), 65536).decode()
                transcript.append(chunk)
                if "Waiting for a GDB connection" in "".join(transcript):
                    break
            else:
                raise TimeoutError("GDB server not ready: " + "".join(transcript))
        command = ["bash", "scripts/lab.sh", "gdb", "-q", "-nx", "-batch", ELF]
        commands = [
            "set pagination off", "set confirm off", "set tcp connect-timeout 5",
            "target remote 127.0.0.1:1234",
            "printf \"INITIAL_PC=%#lx\\n\", $pc",
            "info registers pc sp a0", "x/4wx 0x80000000", "x/4i $pc",
            "stepi", "printf \"STEP_PC=%#lx\\n\", $pc",
            "break *main", "stepi 40000",
            "printf \"AT_MAIN=%d\\n\", $pc == (long)&main",
            "info registers pc sp", "x/4i $pc", "delete breakpoints", "detach",
        ]
        for value in commands:
            command += ["-ex", value]
        result = capture(command, f"{PREFIX}-gdb.txt", 30)
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        for expected in ("INITIAL_PC=0x80000000", "STEP_PC=0x80000004", "AT_MAIN=1", "Breakpoint 1"):
            assert expected in output, f"GDB missing {expected!r}:\n{output}"
        remaining, _ = server.communicate(timeout=5)
        transcript.append(remaining)
        assert server.returncode == 0, "".join(transcript)
        print("GDB Remote: port 1234, registers, memory, disassembly, step and main breakpoint verified")
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                remaining, _ = server.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                remaining, _ = server.communicate()
            transcript.append(remaining)
        save(EVIDENCE / f"{PREFIX}-gdb-server.txt",
             f"COMMAND: {server_command!r}\n{''.join(transcript)}\nEXIT_CODE={server.returncode}\n")


if __name__ == "__main__":
    run_rvdb()
    run_gdb()
