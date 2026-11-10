//! Lab byte-difference instructions. Chapter 2 validates frontend dispatch only.
use super::{RVInstrInfo, normal_exec};
use crate::isa::riscv::{executor::RVCPU, trap::Exception};

fn announce(name: &str, info: RVInstrInfo, cpu: &mut RVCPU) -> Result<(), Exception> {
    let RVInstrInfo::R { rd, rs1, rs2 } = info else {
        return Err(Exception::IllegalInstruction);
    };
    log::info!("[LabCustom] {name} phase=frontend rd={rd} rs1={rs1} rs2={rs2}");
    normal_exec(cpu, |_| Ok(()))
}

pub(super) fn exec_psub8(info: RVInstrInfo, cpu: &mut RVCPU) -> Result<(), Exception> {
    announce("PSUB8", info, cpu)
}

pub(super) fn exec_pabsdiff8(info: RVInstrInfo, cpu: &mut RVCPU) -> Result<(), Exception> {
    announce("PABSDIFF8", info, cpu)
}
