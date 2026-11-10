//! Regression: batch emulation must work without a controlling terminal.
#![cfg(feature = "native-cli")]

use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

#[test]
fn normal_mode_runs_with_redirected_stdio() {
    // RISC-V: write 0x5555 to the board's power-off MMIO register.
    let words = [0x001002b7u32, 0x00005337, 0x55530313, 0x0062a023];
    let path = std::env::temp_dir().join(format!("here-cli-poweroff-{}.bin", std::process::id()));
    let bytes: Vec<_> = words.into_iter().flat_map(u32::to_le_bytes).collect();
    std::fs::write(&path, bytes).unwrap();
    let mut child = Command::new(env!("CARGO_BIN_EXE_here"))
        .args(["--format", "bin", "--max-cycles", "64"])
        .arg(&path)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let deadline = Instant::now() + Duration::from_secs(15);
    while child.try_wait().unwrap().is_none() {
        if Instant::now() >= deadline {
            child.kill().unwrap();
            let output = child.wait_with_output().unwrap();
            panic!("batch CLI timed out: {output:?}");
        }
        std::thread::sleep(Duration::from_millis(10));
    }
    let output = child.wait_with_output().unwrap();
    std::fs::remove_file(path).unwrap();
    assert!(
        output.status.success(),
        "batch CLI failed: status={} stdout={} stderr={}",
        output.status,
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(String::from_utf8_lossy(&output.stdout).contains("Used time:"));
    assert!(!String::from_utf8_lossy(&output.stderr).contains("Max cycles reached"));
}
