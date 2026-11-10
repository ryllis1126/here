# 课程验收映射

2026-11-10 已阅读主页、全部9个章节及附录正文；缓存 `.cache/course/`。关联规范按实现需要继续阅读，下载不等于已读。

| 章节（相对课程根路径） | 个人交付与验收 | 状态 |
|---|---|---|
| [0x00.1](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch0.1/) | nightly兼容、交叉工具链/GDB、重建HERE/裸机、ISA ELF、完整Cargo测试 | 实测通过 |
| [0x00.2](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch0.2/) | rvdb寄存器/内存/反汇编/步进/断点；GDB Remote真实会话 | 实测通过 |
| [0x01](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch1/) | ABI/汇编/ELF/PT_LOAD/链接启动分析；个人终端程序移植与真实交互 | 实测/审查通过；推送暂停 |
| [0x02](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch2/) | 自选一组指令编码/JSON/生成/译码/响应日志；Rust测试；C .insn API及裸机执行 | 前端实测/审查通过；推送暂停 |
| [0x03](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch3/) | ExecTrait后端/路由；正常/0/全1/溢出/通道/x0/PC/流水依赖；C golden model | 实测/审查通过；推送暂停 |
| [0x04](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch4/) | M monitor启动多个U任务；ecall输出/sleep/任务/退出；非ecall异常CSR与恢复；CLINT公平时间片；优先级扩展单列 | 待执行 |
| [0x05](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch5/) | 新增Linux可识别实用设备；MMIO/注册/PLIC；按需后台/DMA/Acquire-Release；Rust/裸机/Linux验证 | 待执行 |
| [0x06](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch6/) | OpenSBI/DTB/BusyBox；Ext4 VirtIO及个人Linux程序；Alpine rootfs/apk/原生GCC；其他发行版探索记录 | 待执行 |
| [0x07](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch7/) | 整数RVV点积/GEMM；编译器向量化；模拟器与标量对照、边界/尾部测试 | 待执行 |

## 资料与当前源码差异

- [附录与Slides](https://heu-cs-dphd.github.io/projects/emu-exp-2026/appendix_a/)：tutorial、riscv_intro已完整阅读。Slides对向量/网卡支持的概括不能代替当前源码，实验遵循当前整数RVV支持范围。
- ch5/ch6的 `src/device/config.rs`、`virtio_blk.rs` 与当前配置模块及 `virtio_block.rs` 名称不同，按实际源码定位。
- ch6 Linux命令误用 `virtio_blk_test.elf`（裸机测试），应使用真正的OpenSBI+Linux镜像并加载DTB。
- ch6 unknown-elf静态编译示例不保证Linux ABI，采用Linux工具链或显式Linux syscall ABI。
- ch4优先级抢占属课程扩展，公平时间片属必做；用户已授权扩展实施，证据分别记录。
- ch6 Alpine属进阶实践，纳入用户要求；其他发行版为探索，不伪称部署成功。
