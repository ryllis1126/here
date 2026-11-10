# HERE 全章节实施计划

> 执行方式：superpowers:executing-plans。用户明确指定master自主开发、通过后提交推送；不另建分支或工作树。

**Goal:** 全章节具备个人实现、实测证据、复现入口和Git里程碑。

**Architecture:** 复用当前CPU/设备框架、test_resources和Makefile。统一脚本和章节记录；优先最小兼容实现。ch2/ch3用自选packed整数指令衔接，ch5优先评估无需宿主特权的VirtIO-RNG。

**Tech Stack:** Rust nightly、GNU RISC-V、C/汇编、rvdb/GDB、VirtIO、OpenSBI/Linux、整数RVV。

**Spec:** 用户总控指令及requirements.md链接的课程原文。

## 全局约束与检查重点

保留master/历史/Tag；仅origin推送；系统改动先批准；同一问题最多三轮实质修复；只操作普通实验镜像；不伪造运行结果。重点：ISA ELF缺失、调试真实交互、RV64高位通道、DMA可见性、Linux ABI与镜像/DTB匹配。

## 任务

- [x] 1. 创建AGENTS、here-lab、docs和统一脚本；运行语法/技能验证及环境检查。
- [x] 2. 0x00.1：复现GDB依赖缺失；修复本地环境；重建HERE/ISA/裸机；main实际运行；完整Cargo测试。
- [ ] 3. 0x00.2：rvdb和GDB真实会话；寄存器/内存/反汇编/步进/断点；回归/记录/commit/Annotated ch0/push。
- [ ] 4. 0x01：定义终端计算器/命令程序交互验收后移植，分析ELF/ABI/启动；回归/记录/commit/ch1/push。
- [ ] 5. 0x02：检查custom编码，选未占用字节运算；先译码测试，再JSON/路由日志/C API；回归/记录/commit/ch2/push。
- [ ] 6. 0x03：先边界/流水测试，再纯算术后端；C参考模型；完整回归/记录/commit/ch3/push。
- [ ] 7. 0x04：先任务/CSR/异常/时间片验收，再monitor/U任务及优先级扩展；回归/记录/commit/ch4/push。
- [ ] 8. 0x05：读VirtIO规范及现有异步队列；先Rust/裸机测试再RNG设备；Linux实际识别读取；回归/记录/commit/ch5/push。
- [ ] 9. 0x06：Linux/DTB/BusyBox、Ext4个人程序、Alpine rootfs及包开发环境；回归/记录/commit/ch6/push。
- [ ] 10. 0x07：先标量数据与边界验收，再整数RVV点积/GEMM/编译器向量化；回归/记录/commit/ch7/push。
- [ ] 11. 全章节清单、全套回归、Tag类型、个人远程成果核验；最终报告/目录/人工事项。

每章开始前在独立记录中细化文件、接口、命令与期望结果；未确定的编码、设备接口和monitor布局在源码分析后确定。
