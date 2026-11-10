# 持续执行进度

当前：工作流和Chapter0实测完成，独立审查后整理提交/Tag/推送；随后进入Chapter1。

基础HEAD：7cd34e277692c5fe6c5a9959b3206e0cff0808ff。2026-11-10开始时master干净、origin/upstream同步，upstream push禁用。

## 决策和证据

- 全部课程章节、附录和两个Slides全文已读；后续关联规范按实现阅读。
- 基线：缺少AGENTS/scripts/实验记录；GDB缺libpython3.10；ISA ELF缺失。
- here-lab技能基线未发现违规判断；技能用于持久化课程入口、验收映射、复现和恢复，不声称修复不存在的行为错误。
- 用户指定master开发，优先于技能默认工作树流程。本文件充当持久执行账本。
- 工作流技能语法和只读行为复测通过；基线无违规，不夸大技能效果。
- Task 1完成：AGENTS/here-lab/文档/统一脚本创建并实际执行，setup-gdb校验包和本地解包通过。
- Task 2完成：GDB环境修复、13裸机重建/main PASS、完整336项Cargo测试和238 ISA ELF通过。
- Task 3调试完成：rvdb与RISC-V GDB Remote真实寄存器、内存、反汇编、步进和断点记录均通过，等待Git里程碑。
- 独立审查修复：Cargo以进程组300秒timeout/5秒kill-after限制；CLI用Rust标准库限时等待15秒并回收，避免平台外部命令依赖；超时保留日志；下载.partial校验后rename。
- Ruling（最终）：GDB不消费--max-cycles，采用原生stepi 40000计数推进，main断点提前命中且AT_MAIN=1；另有30秒宿主超时。真实复跑通过，无需修改GDB功能；此决定替代初拟仅宿主超时方案。

## 章节提交索引

Chapter0全部实测通过；本章提交由Annotated ch0定位，下一次索引更新记录实际SHA和推送结果。创建前已检查本地和origin无ch0，不覆盖已有Tag。
