//! Linux read-ahead can submit segments larger than Tokio File's I/O buffer.
#![cfg(all(feature = "native-cli", feature = "riscv64"))]
use here::{
    DeviceConfig,
    board::virt::{UartIoMode, VirtBoard, VirtBoardConfig},
    isa::{DebugTarget, riscv::debugger::Address},
};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

#[test]
fn block_read_fills_a_segment_larger_than_the_host_io_buffer() {
    let length = 4 * 1024 * 1024;
    let expected: Vec<u8> = (0..length).map(|i| (i % 251) as u8).collect();
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let path = std::env::temp_dir().join(format!(
        "here-large-block-{}-{stamp}.img",
        std::process::id()
    ));
    std::fs::write(&path, &expected).unwrap();
    struct Owned(std::path::PathBuf);
    impl Drop for Owned {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let _owned = Owned(path.clone());
    let device: DeviceConfig = format!("virtio-block:{}", path.display()).parse().unwrap();
    let mut board = VirtBoard::from_binary_with(
        &[0x6f, 0, 0, 0],
        VirtBoardConfig::new()
            .with_uart_io(UartIoMode::None)
            .with_virtio_devices(vec![device]),
    )
    .unwrap();
    let mmio = 0x10001000;
    let mut reg = |offset, value: u32| {
        board
            .cpu
            .write_memory(Address::Phys(mmio + offset), value)
            .unwrap()
    };
    reg(0x70, 3);
    reg(0x24, 1);
    reg(0x20, 1);
    reg(0x70, 11);
    reg(0x30, 0);
    reg(0x38, 8);
    for (offset, address) in [(0x80, 0x80001000), (0x90, 0x80002000), (0xa0, 0x80003000)] {
        reg(offset, address);
        reg(offset + 4, 0);
    }
    let header = 0x80004000;
    let status = 0x80005000;
    let data = 0x80010000;
    for (i, (address, len, flags, next)) in [
        (header, 16u32, 1u16, 1u16),
        (data, length as u32, 3, 2),
        (status, 1, 2, 0),
    ]
    .into_iter()
    .enumerate()
    {
        let desc = 0x80001000 + i as u64 * 16;
        board
            .cpu
            .write_memory(Address::Phys(desc), address)
            .unwrap();
        board
            .cpu
            .write_memory(Address::Phys(desc + 8), len)
            .unwrap();
        board
            .cpu
            .write_memory(Address::Phys(desc + 12), flags)
            .unwrap();
        board
            .cpu
            .write_memory(Address::Phys(desc + 14), next)
            .unwrap();
    }
    board.cpu.write_memory(Address::Phys(header), 0u64).unwrap(); // READ, reserved=0
    board
        .cpu
        .write_memory(Address::Phys(header + 8), 0u64)
        .unwrap(); // sector=0
    board
        .cpu
        .write_memory(Address::Phys(status), 0xffu8)
        .unwrap();
    board
        .cpu
        .write_memory(Address::Phys(0x80002004), 0u16)
        .unwrap();
    board
        .cpu
        .write_memory(Address::Phys(0x80002002), 1u16)
        .unwrap();
    for (offset, value) in [(0x44, 1u32), (0x70, 15), (0x50, 0)] {
        board
            .cpu
            .write_memory(Address::Phys(mmio + offset), value)
            .unwrap();
    }
    let deadline = Instant::now() + Duration::from_secs(5);
    while board
        .cpu
        .read_memory::<u32>(Address::Phys(mmio + 0x60))
        .unwrap()
        == 0
    {
        assert!(Instant::now() < deadline, "block completion timed out");
        std::thread::sleep(Duration::from_millis(1));
    }
    assert_eq!(
        board.cpu.read_memory::<u8>(Address::Phys(status)).unwrap(),
        0,
        "large valid read must not return IOERR"
    );
    assert_eq!(
        board
            .cpu
            .read_memory::<u32>(Address::Phys(0x80003008))
            .unwrap(),
        length as u32 + 1
    );
    for offset in (0..length).step_by(4096).chain([length - 1]) {
        assert_eq!(
            board
                .cpu
                .read_memory::<u8>(Address::Phys(data + offset as u64))
                .unwrap(),
            expected[offset]
        );
    }
}
