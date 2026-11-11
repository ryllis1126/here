# 持续执行进度

当前：Chapter 0x00.1 至 0x07 已通过本地验收。master 和 9 个附注标签已发布到个人 origin，远端引用已核验。

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
- Task 4本地验收通过：宿主UBSan与HERE UART各16例；热重启BSS回归先红后绿；336项Cargo/ISA及rvdb/GDB回归通过；独立审查无问题。ch1提交由Tag定位，下一章记录实际SHA；所有推送继续暂停。
- Task 5本地验收通过：PSUB8/PABSDIFF8编码/JSON/生成/译码/响应日志/C调用链；新测试先红后绿，default337和custom339项全绿0忽略；原display样例取消忽略并加强PC/退休断言；Chapter1回归通过。独立审查及隔离复跑无问题。
- Task 6本地验收通过：两个ExecTrait后端，通道/x0/alias/PC环绕/退休/流水测试先红后绿；1056次C参考比较和每指令528条日志；default337/custom342项全绿，前章回归通过。Makefile头文件依赖及库规则$<问题已实测修复，独立审查确认无剩余问题。
- Chapter3补充：UART退出取消丢队列已修复，8192字节取消测试先红后绿，16384字节真实CLI突发输出完整；default339/custom344项通过，C对照连续20次模拟器运行通过，独立审查无剩余问题。原ch3内的一次失败证据如实保留，补充Tag ch3-fix1不覆盖原Tag。后续提交关卡使用set-e串行验收并等待命令终态。
- Task 7本地验收通过：4个U任务/M monitor与idle、ecall服务、非法指令跳过/非法CSR终止、精确CSR/nm对照，CLINT轮转7/8次、14次公平切换，优先级创建/唤醒抢占、sleep/yield/exit；tp回归先红后绿，339/344项及原示例/前章回归通过，独立审查无问题。

## 章节提交索引

| 章节 | Commit | Annotated Tag | origin |
|---|---|---|---|
| 0x00.1+0x00.2 | 0826729 | ch0 | 已核验 |
| 0x01 | 02d8f9c | ch1 | 已核验 |
| 0x02 | 5f02412 | ch2 | 已核验 |
| 0x03原始 | 65b5a51 | ch3 | 已核验，保留 UART 竞态的原始记录 |
| 0x03补充验收 | fa18065 | ch3-fix1 | 已核验，包含 UART 修复和复验 |
| 0x04 | edbeb24 | ch4 | 已核验 |
| 0x05 | dc36f42 | ch5 | 已核验 |
| 0x06 | d722353 | ch6 | 已核验 |
| 0x07 | 26a13c7 | ch7 | 已核验 |

首次推送因 HTTPS 无凭据退出 128。WSL 登录恢复后，2026-11-11 原子推送 master 和上述附注标签。远端 master、9 个标签对象及其所指提交均与本地匹配。

- Task 8本地验收通过：全新VirtIO-RNG，6项公开MMIO测试、真实裸机2次DMA/IRQ、Linux原生virtio_rng.0和/dev/hwrng读取32字节，345/350项及前章回归全部通过；独立审查无Critical/Important问题，补充分散描述符链测试。ch5由Tag定位，下一章补实际SHA。

- Chapter 6 本地验收通过。BusyBox 计算器和 Ext4 持久化、Alpine 切根、APK 安装及原生 GCC 运行均有串口证据。修复 VirtIO Block 4 MiB 短读，默认 346 项与自定义指令 351 项回归通过。

- Chapter 7 本地验收通过。RVV 点积和 Clang AXPY 分别检查 14 个长度，GEMM 检查 7 个形状。AVL x0 回归先失败后通过，最终默认 347 项和自定义指令 352 项均通过。
