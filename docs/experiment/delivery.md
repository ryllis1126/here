# HERE 2026 实验交付

本地实测覆盖 Chapter 0x00.1 至 0x07。各章命令、结果和源码入口见 [验收映射](requirements.md) 与 [章节索引](README.md)。

| 章节 | 附注标签 | 本地验收要点 |
|---|---|---|
| 0x00.1 / 0x00.2 | ch0 | 项目工具链、ISA ELF、真实 rvdb 和 GDB Remote |
| 0x01 | ch1 | 计算器宿主与 UART、ABI、热重启 BSS |
| 0x02 | ch2 | PSUB8/PABSDIFF8 编码、生成译码、C API、执行日志 |
| 0x03 | ch3、ch3-fix1 | 执行后端与 1056 次标量对照。ch3-fix1 修复退出时 UART 丢失并完成连续复验 |
| 0x04 | ch4 | M-mode monitor、U-mode 任务、异常和 CSR、CLINT 轮转与优先级抢占 |
| 0x05 | ch5 | VirtIO RNG、DMA 和 PLIC，Linux 实际读取 32 字节 |
| 0x06 | ch6 | OpenSBI、BusyBox 与 Linux ABI 程序、Ext4 持久化、Alpine 与原生 GCC |
| 0x07 | ch7 | 整数 RVV 点积、GEMM、Clang 自动向量化与标量对照 |

最终默认套件 347 项和自定义指令套件 352 项均通过，含覆盖 238 个 ELF 的 8 组 ISA 测试。模拟器串口和调试器会话、块镜像与 Alpine 原生编译的运行记录分开保存。[默认套件](evidence/ch7-default-tests.txt) · [自定义指令套件](evidence/ch7-custom-tests.txt) · [RVV](evidence/ch7-rvv-final.txt) · [BusyBox](evidence/ch7-linux-disk.txt) · [Alpine](evidence/ch7-alpine.txt)

2026-11-11，个人 origin 的 master 和 9 个附注标签已通过一次原子推送发布。发布时 master 指向验收提交 `26a13c72365eca7490936dcd904af22da1683bff`。用 `git ls-remote origin refs/heads/master 'refs/tags/ch*'` 核验了分支、标签对象和标签所指提交，均与本地一致。[个人 origin](https://github.com/ryllis1126/here)
