//! VirtIO entropy device (ID 4), using the shared MMIO/split-queue transport.
use crate::{
    device::virtio::{
        config::{VIRTQUEUE_MAX_SIZE, VirtIOFeatureSet, virtio_reserved_feature},
        virtio_device::{VirtIODeviceEnum, VirtIODeviceTrait},
        virtio_mmio::VirtIODeviceStatus,
        virtio_queue::{VirtQueue, VirtQueueCompletion},
    },
    task_spawner::{DeviceTask, TaskSpawner},
};
use std::{
    path::Path,
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicU8, Ordering},
    },
};
use tokio::{
    fs::File,
    io::AsyncReadExt,
    sync::{mpsc, watch},
};

const MAX_ENTROPY_BYTES: usize = 4096;

struct Buffer {
    address: usize,
    len: usize,
}
enum Request {
    Fill {
        buffers: Vec<Buffer>,
        completion: VirtQueueCompletion,
    },
    Barrier(std::sync::mpsc::SyncSender<()>),
}

struct EntropyWorker {
    source: File,
    requests: mpsc::Receiver<Request>,
    isr: Arc<AtomicU8>,
    broken: Arc<AtomicBool>,
}

impl DeviceTask for EntropyWorker {
    async fn run(mut self, mut cancel: watch::Receiver<bool>) {
        loop {
            let request = tokio::select! {
                biased;
                _ = cancel.changed() => { self.requests.close(); self.requests.recv().await }
                request = self.requests.recv() => request,
            };
            let Some(request) = request else { return };
            match request {
                Request::Barrier(done) => {
                    let _ = done.send(());
                }
                Request::Fill {
                    buffers,
                    completion,
                } => {
                    let len = buffers.iter().map(|b| b.len).sum();
                    let mut bytes = vec![0u8; len];
                    // Stage host I/O before touching guest memory: an error cannot
                    // leave a partially filled guest buffer looking completed.
                    let success = !self.broken.load(Ordering::Acquire)
                        && (len == 0 || self.source.read_exact(&mut bytes).await.is_ok());
                    if success {
                        let mut offset = 0;
                        for buffer in buffers {
                            // VirtQueue validated every range. Board task shutdown
                            // and reset barriers keep RAM alive until completion.
                            unsafe {
                                std::ptr::copy_nonoverlapping(
                                    bytes.as_ptr().add(offset),
                                    buffer.address as *mut u8,
                                    buffer.len,
                                )
                            };
                            offset += buffer.len;
                        }
                        completion.complete(len as u32);
                        self.isr.fetch_or(1, Ordering::Release);
                    } else {
                        self.broken.store(true, Ordering::Release);
                        completion.complete(0);
                        self.isr.fetch_or(2, Ordering::Release); // configuration/status error
                    }
                }
            }
        }
    }
}

pub(crate) struct VirtIORngDevice {
    status: u8,
    guest_features: VirtIOFeatureSet,
    queue: VirtQueue,
    ram_base: usize,
    requests: mpsc::Sender<Request>,
    isr: Arc<AtomicU8>,
    broken: Arc<AtomicBool>,
}

impl VirtIORngDevice {
    pub(crate) fn new(ram_base: *mut u8, source: &Path, spawner: &mut TaskSpawner) -> Self {
        let source = std::fs::File::open(source).unwrap_or_else(|error| {
            panic!("cannot open entropy source {}: {error}", source.display())
        });
        let (sender, requests) = mpsc::channel(VIRTQUEUE_MAX_SIZE as usize);
        let isr = Arc::new(AtomicU8::new(0));
        let broken = Arc::new(AtomicBool::new(false));
        spawner.register(EntropyWorker {
            source: File::from_std(source),
            requests,
            isr: isr.clone(),
            broken: broken.clone(),
        });
        Self {
            status: 0,
            guest_features: 0,
            queue: VirtQueue::new(ram_base, 0),
            ram_base: ram_base as usize,
            requests: sender,
            isr,
            broken,
        }
    }
}

impl VirtIODeviceTrait for VirtIORngDevice {
    fn get_device_id(&self) -> u16 {
        VirtIODeviceEnum::VirtIORng as u16
    }
    fn status(&mut self) -> &mut u8 {
        if self.broken.load(Ordering::Acquire) {
            self.status |= VirtIODeviceStatus::DEVICE_NEEDS_RESET.bits();
        }
        &mut self.status
    }
    fn get_generation(&self) -> u32 {
        0
    }
    fn reset(&mut self) {
        // FIFO barrier: no old worker DMA may cross the reset boundary.
        let (done, wait) = std::sync::mpsc::sync_channel(0);
        if self.requests.blocking_send(Request::Barrier(done)).is_ok() {
            let _ = wait.recv();
        }
        self.status = 0;
        self.guest_features = 0;
        self.queue.reset();
        self.isr.store(0, Ordering::Release);
        self.broken.store(false, Ordering::Release);
    }
    fn isr(&self) -> &AtomicU8 {
        &self.isr
    }
    fn irq_level(&mut self) -> bool {
        let isr = self.isr.load(Ordering::Acquire);
        isr & 2 != 0 || (isr & 1 != 0 && self.queue.interrupts_enabled())
    }
    fn get_host_feature(&self) -> VirtIOFeatureSet {
        virtio_reserved_feature::VERSION_1
    }
    fn set_feature(&mut self, features: VirtIOFeatureSet) {
        if features != virtio_reserved_feature::VERSION_1 {
            self.status &= !VirtIODeviceStatus::FEATURES_OK.bits();
        } else {
            self.guest_features = features;
        }
    }
    fn set_queue_num(&mut self, num: u32) {
        self.queue.set_queue_num(num);
    }
    fn queue_ready(&self) -> bool {
        self.queue.ready()
    }
    fn queue_select(&self, _idx: u32) {}
    fn get_num_of_queue(&self) -> u32 {
        1
    }
    fn set_desc(&mut self, addr: u64) {
        self.queue.set_desc(addr);
    }
    fn set_avail(&mut self, addr: u64) {
        self.queue.set_avail(addr);
    }
    fn set_used(&mut self, addr: u64) {
        self.queue.set_used(addr);
    }
    fn manage_one_request(&mut self) -> bool {
        if self.status & VirtIODeviceStatus::DRIVER_OK.bits() == 0
            || self.status & VirtIODeviceStatus::FEATURES_OK.bits() == 0
            || self.broken.load(Ordering::Acquire)
        {
            return false;
        }
        let Ok(permit) = self.requests.try_reserve() else {
            return false;
        };
        let mut buffers = Vec::new();
        let mut remaining = MAX_ENTROPY_BYTES;
        let mut valid = true;
        let ram_base = self.ram_base;
        let Some(completion) = self.queue.take_one_request(|desc, _| {
            if !desc.device_writable() {
                valid = false;
                return;
            }
            let len = (desc.len as usize).min(remaining);
            if len != 0 {
                buffers.push(Buffer {
                    address: desc.get_request_package::<u8>(ram_base) as usize,
                    len,
                });
                remaining -= len;
            }
        }) else {
            return false;
        };
        if !valid {
            buffers.clear();
        }
        permit.send(Request::Fill {
            buffers,
            completion,
        });
        true
    }
    fn notify(&mut self, queue: u32) {
        if queue == 0 {
            while self.manage_one_request() {}
        }
    }
    fn read_config(&mut self, _offset: u64, _len: u32) -> u64 {
        0
    }
    fn write_config(&mut self, _offset: u64, _len: u32, _data: u64) {}
}
