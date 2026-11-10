//! Byte-difference execution: arithmetic is independent of CPU state.
use super::{
    RVInstrInfo,
    exec_function::{ExecTrait, exec_arith},
};
use crate::{
    config::arch_config::WordType,
    isa::riscv::{executor::RVCPU, trap::Exception},
};

struct ExecPsub8;

impl ExecTrait<Result<WordType, Exception>> for ExecPsub8 {
    fn exec(a: WordType, b: WordType) -> Result<WordType, Exception> {
        let (a, b) = (a.to_le_bytes(), b.to_le_bytes());
        let mut result = [0u8; size_of::<WordType>()];
        for i in 0..result.len() {
            result[i] = a[i].wrapping_sub(b[i]);
        }
        Ok(WordType::from_le_bytes(result))
    }
}

struct ExecPabsdiff8;

impl ExecTrait<Result<WordType, Exception>> for ExecPabsdiff8 {
    fn exec(a: WordType, b: WordType) -> Result<WordType, Exception> {
        let (a, b) = (a.to_le_bytes(), b.to_le_bytes());
        let mut result = [0u8; size_of::<WordType>()];
        for i in 0..result.len() {
            result[i] = a[i].abs_diff(b[i]);
        }
        Ok(WordType::from_le_bytes(result))
    }
}

fn execute<F>(name: &str, info: RVInstrInfo, cpu: &mut RVCPU) -> Result<(), Exception>
where
    F: ExecTrait<Result<WordType, Exception>>,
{
    let RVInstrInfo::R { rd, rs1, rs2 } = info else {
        return Err(Exception::IllegalInstruction);
    };
    log::info!("[LabCustom] {name} phase=backend rd={rd} rs1={rs1} rs2={rs2}");
    exec_arith::<F>(info, cpu)
}

pub(super) fn exec_psub8(info: RVInstrInfo, cpu: &mut RVCPU) -> Result<(), Exception> {
    execute::<ExecPsub8>("PSUB8", info, cpu)
}

pub(super) fn exec_pabsdiff8(info: RVInstrInfo, cpu: &mut RVCPU) -> Result<(), Exception> {
    execute::<ExecPabsdiff8>("PABSDIFF8", info, cpu)
}
