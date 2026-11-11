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

master 的推送目标为个人 origin。2026-11-11 的远端只读检查确认 origin/master 仍指向 7cd34e277692c5fe6c5a9959b3206e0cff0808ff，尚无章节标签。WSL 的 gh auth status 显示未登录。完成 WSL GitHub HTTPS 认证后，向个人 origin 推送 master、ch0 至 ch7 以及 ch3-fix1，并核对远端附注标签对象和 peeled commit。
