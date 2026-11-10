//! Exercise the entropy device through the same public MMIO path a guest uses.
#![cfg(all(feature = "native-cli", feature = "riscv64"))]
use here::{
    DeviceConfig,
    board::virt::{UartIoMode, VirtBoard, VirtBoardConfig},
    isa::{DebugTarget, riscv::debugger::Address},
};
use std::{
    path::PathBuf,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

const MMIO: u64 = 0x10001000;
const DESC: u64 = 0x80001000;
const AVAIL: u64 = 0x80002000;
const USED: u64 = 0x80003000;
const DATA: u64 = 0x80004000;

struct Source(PathBuf);
impl Source {
    fn new(bytes: &[u8]) -> Self {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path =
            std::env::temp_dir().join(format!("here-entropy-{}-{stamp}", std::process::id()));
        std::fs::write(&path, bytes).unwrap();
        Self(path)
    }
}
impl Drop for Source {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn board(source: &Source) -> VirtBoard {
    let config: DeviceConfig = format!("virtio-rng:{}", source.0.display())
        .parse()
        .expect("virtio-rng must be configurable");
    VirtBoard::from_binary_with(
        &[0x6f, 0, 0, 0],
        VirtBoardConfig::new()
            .with_uart_io(UartIoMode::None)
            .with_virtio_devices(vec![config]),
    )
    .unwrap()
}
fn write(board: &mut VirtBoard, offset: u64, value: u32) {
    board
        .cpu
        .write_memory(Address::Phys(MMIO + offset), value)
        .unwrap();
}
fn read(board: &mut VirtBoard, offset: u64) -> u32 {
    board.cpu.read_memory(Address::Phys(MMIO + offset)).unwrap()
}
fn configure(board: &mut VirtBoard, length: u32, writable: bool) {
    assert_eq!(read(board, 0), 0x74726976);
    assert_eq!(read(board, 8), 4);
    write(board, 0x70, 3);
    write(board, 0x14, 1);
    assert_eq!(read(board, 0x10) & 1, 1);
    write(board, 0x24, 1);
    write(board, 0x20, 1);
    write(board, 0x70, 11);
    assert_ne!(read(board, 0x70) & 8, 0);
    write(board, 0x30, 0);
    write(board, 0x38, 8);
    for (offset, address) in [(0x80, DESC), (0x90, AVAIL), (0xa0, USED)] {
        write(board, offset, address as u32);
        write(board, offset + 4, 0);
    }
    board.cpu.write_memory(Address::Phys(DESC), DATA).unwrap();
    board
        .cpu
        .write_memory(Address::Phys(DESC + 8), length)
        .unwrap();
    board
        .cpu
        .write_memory(Address::Phys(DESC + 12), if writable { 2u16 } else { 0 })
        .unwrap();
    board
        .cpu
        .write_memory(Address::Phys(DESC + 14), 0u16)
        .unwrap();
    board.cpu.write_memory(Address::Phys(AVAIL), 0u16).unwrap();
    board
        .cpu
        .write_memory(Address::Phys(AVAIL + 2), 1u16)
        .unwrap();
    board
        .cpu
        .write_memory(Address::Phys(AVAIL + 4), 0u16)
        .unwrap();
    for offset in 0..64 {
        board
            .cpu
            .write_memory(Address::Phys(DATA + offset), 0xccu8)
            .unwrap();
    }
    write(board, 0x44, 1);
    assert_eq!(read(board, 0x44), 1);
    write(board, 0x70, 15);
}
fn complete(board: &mut VirtBoard) -> u32 {
    write(board, 0x50, 0);
    let deadline = Instant::now() + Duration::from_secs(5);
    while read(board, 0x60) == 0 {
        assert!(Instant::now() < deadline, "entropy completion timed out");
        std::thread::sleep(Duration::from_millis(1));
    }
    // ISR Acquire synchronizes the DMA and used-ring writes before reading RAM.
    assert_eq!(
        board
            .cpu
            .read_memory::<u16>(Address::Phys(USED + 2))
            .unwrap(),
        1
    );
    board.cpu.read_memory(Address::Phys(USED + 8)).unwrap()
}

#[test]
fn entropy_dma_interrupt_ack_and_reset() {
    let source = Source::new(&(0..128u8).collect::<Vec<_>>());
    let mut board = board(&source);
    configure(&mut board, 64, true);
    assert_eq!(complete(&mut board), 64);
    for i in 0..64 {
        assert_eq!(
            board
                .cpu
                .read_memory::<u8>(Address::Phys(DATA + i))
                .unwrap(),
            i as u8
        );
    }
    write(&mut board, 0x64, 1);
    assert_eq!(read(&mut board, 0x60), 0);
    write(&mut board, 0x70, 0);
    assert_eq!(read(&mut board, 0x70), 0);
    assert_eq!(read(&mut board, 0x44), 0);
    assert_eq!(read(&mut board, 0x60), 0);
}

#[test]
fn entropy_rejects_device_readable_buffers() {
    let source = Source::new(&[0x55; 64]);
    let mut board = board(&source);
    configure(&mut board, 64, false);
    assert_eq!(complete(&mut board), 0);
    for i in 0..64 {
        assert_eq!(
            board
                .cpu
                .read_memory::<u8>(Address::Phys(DATA + i))
                .unwrap(),
            0xcc
        );
    }
}

#[test]
fn entropy_caps_a_large_request_without_overwriting_its_tail() {
    let source = Source::new(&[0x5a; 4096]);
    let mut board = board(&source);
    configure(&mut board, 8192, true);
    board
        .cpu
        .write_memory(Address::Phys(DATA + 4096), 0xaau8)
        .unwrap();
    assert_eq!(complete(&mut board), 4096);
    assert_eq!(
        board
            .cpu
            .read_memory::<u8>(Address::Phys(DATA + 4095))
            .unwrap(),
        0x5a
    );
    assert_eq!(
        board
            .cpu
            .read_memory::<u8>(Address::Phys(DATA + 4096))
            .unwrap(),
        0xaa
    );
}

#[test]
fn entropy_source_failure_requests_reset_and_preserves_guest_data() {
    let source = Source::new(&[]);
    let mut board = board(&source);
    configure(&mut board, 64, true);
    assert_eq!(complete(&mut board), 0);
    assert_ne!(
        read(&mut board, 0x70) & 64,
        0,
        "failed source requires device reset"
    );
    assert_ne!(
        read(&mut board, 0x60) & 2,
        0,
        "configuration interrupt reports source failure"
    );
    assert_eq!(
        board.cpu.read_memory::<u8>(Address::Phys(DATA)).unwrap(),
        0xcc
    );
    write(&mut board, 0x70, 0);
    assert_eq!(read(&mut board, 0x70), 0);
    assert_eq!(read(&mut board, 0x60), 0);
}

#[test]
fn entropy_reset_waits_for_an_outstanding_request() {
    let source = Source::new(&[0x5a; 64]);
    let mut board = board(&source);
    configure(&mut board, 64, true);
    write(&mut board, 0x50, 0);
    write(&mut board, 0x70, 0); // Must wait for the already-submitted DMA.
    assert_eq!(
        board
            .cpu
            .read_memory::<u16>(Address::Phys(USED + 2))
            .unwrap(),
        1
    );
    assert_eq!(
        board.cpu.read_memory::<u8>(Address::Phys(DATA)).unwrap(),
        0x5a
    );
    assert_eq!(read(&mut board, 0x60), 0);
    assert_eq!(read(&mut board, 0x70), 0);
    board.cpu.write_memory(Address::Phys(DATA), 0xccu8).unwrap();
    std::thread::sleep(Duration::from_millis(10));
    assert_eq!(
        board.cpu.read_memory::<u8>(Address::Phys(DATA)).unwrap(),
        0xcc
    );
}

#[test]
fn entropy_fills_a_scattered_descriptor_chain() {
    let source = Source::new(&(0..64u8).collect::<Vec<_>>());
    let mut board = board(&source);
    configure(&mut board, 16, true);
    // First writable descriptor continues to a separate 48-byte buffer.
    board
        .cpu
        .write_memory(Address::Phys(DESC + 12), 3u16)
        .unwrap();
    board
        .cpu
        .write_memory(Address::Phys(DESC + 14), 1u16)
        .unwrap();
    let second = DATA + 0x100;
    board
        .cpu
        .write_memory(Address::Phys(DESC + 16), second)
        .unwrap();
    board
        .cpu
        .write_memory(Address::Phys(DESC + 24), 48u32)
        .unwrap();
    board
        .cpu
        .write_memory(Address::Phys(DESC + 28), 2u16)
        .unwrap();
    board
        .cpu
        .write_memory(Address::Phys(DESC + 30), 0u16)
        .unwrap();
    assert_eq!(complete(&mut board), 64);
    for i in 0..64u64 {
        let address = if i < 16 { DATA + i } else { second + i - 16 };
        assert_eq!(
            board.cpu.read_memory::<u8>(Address::Phys(address)).unwrap(),
            i as u8
        );
    }
    assert_eq!(
        board
            .cpu
            .read_memory::<u8>(Address::Phys(DATA + 16))
            .unwrap(),
        0xcc
    );
}
