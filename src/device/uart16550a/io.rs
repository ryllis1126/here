use tokio::sync::mpsc::{
    Sender, UnboundedReceiver,
    error::{TryRecvError, TrySendError},
};

#[cfg(feature = "native-cli")]
use crate::task_spawner::DeviceTask;

pub const UART_INPUT_CAPACITY: usize = 1024;

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum UartIoMode {
    None,
    #[default]
    External,
    #[cfg(feature = "native-cli")]
    Stdio,
}

#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum UartIoError {
    #[error("UART host I/O is unavailable in {0:?} mode")]
    Unavailable(UartIoMode),
    #[error("UART input buffer is full after accepting {accepted} bytes")]
    InputFull { accepted: usize },
    #[error("UART input channel is closed after accepting {accepted} bytes")]
    InputClosed { accepted: usize },
}

pub struct UartBytePort {
    pub input_tx: Sender<u8>,
    pub output_rx: UnboundedReceiver<u8>,
}

impl UartBytePort {
    pub fn input_sender(&self) -> Sender<u8> {
        self.input_tx.clone()
    }

    pub fn push_input(&self, bytes: &[u8]) -> Result<(), UartIoError> {
        for (accepted, &byte) in bytes.iter().enumerate() {
            match self.input_tx.try_send(byte) {
                Ok(()) => {}
                Err(TrySendError::Full(_)) => {
                    return Err(UartIoError::InputFull { accepted });
                }
                Err(TrySendError::Closed(_)) => {
                    return Err(UartIoError::InputClosed { accepted });
                }
            }
        }
        Ok(())
    }

    pub fn take_output(&mut self) -> Vec<u8> {
        let mut output = Vec::new();
        loop {
            match self.output_rx.try_recv() {
                Ok(byte) => output.push(byte),
                Err(TryRecvError::Empty | TryRecvError::Disconnected) => return output,
            }
        }
    }
}

#[cfg(feature = "native-cli")]
impl DeviceTask for UartBytePort {
    async fn run(self, cancel: tokio::sync::watch::Receiver<bool>) {
        if let Err(error) = forward_output(self.output_rx, cancel, std::io::stdout()).await {
            log::error!("failed to write UART output to stdout: {error}");
        }
    }

    async fn run_simple(self) {
        let (_keep_open, cancel) = tokio::sync::watch::channel(false);
        self.run(cancel).await;
    }
}

#[cfg(feature = "native-cli")]
async fn forward_output<W: std::io::Write>(
    mut receiver: UnboundedReceiver<u8>,
    mut cancel: tokio::sync::watch::Receiver<bool>,
    mut writer: W,
) -> std::io::Result<W> {
    let mut buffer = [0u8; 4096];
    loop {
        let byte = tokio::select! {
            biased;
            _ = cancel.changed() => {
                // Stop accepting new output, then drain every already-queued byte.
                receiver.close();
                receiver.recv().await
            }
            byte = receiver.recv() => byte,
        };
        let Some(byte) = byte else { break };
        buffer[0] = byte;
        let mut len = 1;
        while len < buffer.len() {
            match receiver.try_recv() {
                Ok(byte) => {
                    buffer[len] = byte;
                    len += 1;
                }
                Err(_) => break,
            }
        }

        writer.write_all(&buffer[..len])?;
        writer.flush()?;
    }
    Ok(writer)
}

#[cfg(all(test, feature = "native-cli"))]
mod output_tests {
    use super::*;

    #[tokio::test]
    async fn cancellation_preserves_all_queued_bytes() {
        // Both branches are ready; every permitted select order must retain data.
        for _ in 0..64 {
            let (sender, receiver) = tokio::sync::mpsc::unbounded_channel();
            let expected: Vec<u8> = (0..8192).map(|i| (i % 251) as u8).collect();
            for &byte in &expected {
                sender.send(byte).unwrap();
            }
            let (cancel_tx, cancel_rx) = tokio::sync::watch::channel(false);
            cancel_tx.send(true).unwrap();
            let actual = forward_output(receiver, cancel_rx, Vec::new())
                .await
                .unwrap();
            assert_eq!(actual.len(), expected.len(), "UART cancellation lost bytes");
            assert_eq!(
                actual, expected,
                "UART cancellation discarded queued output"
            );
        }
    }
}
