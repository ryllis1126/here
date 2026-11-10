//! Regression: batch emulation must work without a controlling terminal.
#![cfg(feature = "native-cli")]

use std::io::Read;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

fn run_guest(path: &std::path::Path, cycles: &str) -> std::process::Output {
    let mut child = Command::new(env!("CARGO_BIN_EXE_here"))
        .args(["--format", "bin", "--max-cycles", cycles])
        .arg(path)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let mut stdout = child.stdout.take().unwrap();
    let mut stderr = child.stderr.take().unwrap();
    let out = std::thread::spawn(move || {
        let mut bytes = Vec::new();
        stdout.read_to_end(&mut bytes).unwrap();
        bytes
    });
    let err = std::thread::spawn(move || {
        let mut bytes = Vec::new();
        stderr.read_to_end(&mut bytes).unwrap();
        bytes
    });
    let deadline = Instant::now() + Duration::from_secs(15);
    let status = loop {
        if let Some(status) = child.try_wait().unwrap() {
            break status;
        }
        if Instant::now() >= deadline {
            child.kill().unwrap();
            child.wait().unwrap();
            panic!(
                "batch CLI timed out: stdout={:?} stderr={:?}",
                out.join(),
                err.join()
            );
        }
        std::thread::sleep(Duration::from_millis(10));
    };
    std::process::Output {
        status,
        stdout: out.join().unwrap(),
        stderr: err.join().unwrap(),
    }
}

#[test]
fn normal_mode_runs_with_redirected_stdio() {
    // RISC-V: write 0x5555 to the board's power-off MMIO register.
    let words = [0x001002b7u32, 0x00005337, 0x55530313, 0x0062a023];
    let path = std::env::temp_dir().join(format!("here-cli-poweroff-{}.bin", std::process::id()));
    let bytes: Vec<_> = words.into_iter().flat_map(u32::to_le_bytes).collect();
    std::fs::write(&path, bytes).unwrap();
    let output = run_guest(&path, "64");
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

#[test]
fn immediate_poweroff_preserves_uart_output() {
    // Queue a burst larger than the UART worker buffer, then immediately stop.
    let mut words = vec![0x100002b7u32, 0x05a00313]; // UART base; ASCII Z
    words.extend(std::iter::repeat_n(0x00628023u32, 16384)); // sb t1,0(t0)
    words.extend([0x001002b7, 0x00005337, 0x55530313, 0x0062a023]);
    let path = std::env::temp_dir().join(format!("here-uart-drain-{}.bin", std::process::id()));
    let bytes: Vec<_> = words.into_iter().flat_map(u32::to_le_bytes).collect();
    std::fs::write(&path, bytes).unwrap();
    let output = run_guest(&path, "20000");
    std::fs::remove_file(path).unwrap();
    assert!(output.status.success(), "{output:?}");
    let count = output.stdout.iter().filter(|&&byte| byte == b'Z').count();
    assert_eq!(count, 16384, "queued UART bytes lost on board shutdown");
}
