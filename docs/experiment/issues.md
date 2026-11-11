# 问题与修复账本

| ID | 根因证据 | 实质修复轮次 | 状态 |
|---|---|---:|---|
| ENV-GDB | ldd缺libpython3.10，GDB不能启动 | 1/3 | 已解决：Ubuntu匹配ABI库项目内解包；--version和Remote会话通过 |
| ENV-ISA | riscv-tests/isa无测试ELF | 1/3 | 已解决：GNU工具链构建，8组238ELF实际通过，无新增排除 |
| CLI-NOTTY | main无条件开启rawmode，重定向运行退出2 | 1/3 | 已解决：回归先红后绿；仅TTY开启guard；完整回归通过 |
| GIT-AUTH | origin push 退出 128，HTTPS 无可用凭据 | 0/3 | 已解决。联网验证 WSL 登录身份，原子推送个人 origin 并核验远端分支和标签 |
| BOOT-BSS | boot.S标注清BSS却遍历栈；热重启写脏BSS测试实际失败 | 1/3 | 已解决：startbss/endbss，修复前FAIL、修复后PASS；.data保留，完整回归通过 |
| UART-EXIT | DeviceTask默认cancel分支丢弃UART worker，末尾输出间歇丢失；8192字节预取消实测只写0字节 | 1/3 | 已解决：关闭并排空接收队列，339/344项和连续20次C回归通过，独立审查通过；补充版本ch3-fix1 |
| CH3-GATE | 验证进程尚未结束即触发Git，ch3 Tag含一次缺PASS输出的失败证据 | — | 保留历史与Tag，明确标记原Tag问题；补充修复提交，不覆盖Tag；后续Git关卡使用set-e并等待全部验证终态 |
| LINUX-DEVNODE | Linux virtio_rng.0已注册但课程initramfs无/dev/hwrng，dd READ_STATUS=1 | 1/3 | 已解决：来宾mdev -s生成sysfs的10:183节点，真实32字节读取及正常关机通过 |
| ALPINE-ROOT | 内置 initramfs 缺少 /root，直接挂载返回 ENOENT | 1/3 | 早期 PID 1 挂载并 switch_root，来宾证明 /dev/vda 为 Ext4 根 |
| BLK-SHORT-READ | 4 MiB MMIO 读返回 IOERR，Alpine APK 解包报告磁盘错误 | 1/3 | 按实际字节数读取至完整段，MMIO 回归及干净镜像安装通过 |
| RVV-AVL | 点积 n=0 先失败，Rust 复现 x0 AVL 请求得到 VL=0 而非 VLMAX=4 | 1/3 | 根据 rs1 与 rd 区分 VLMAX、保留 VL、普通寄存器 AVL，Rust 和裸机回归通过 |
| TRAP-TP | 原trap.S不保存/恢复tp，U任务初次上下文断言实际失败 | 1/3 | 已解决：保存x0/tp并恢复tp，monitor与原ecall/trap/CLINT示例、全套及前章回归通过 |

调试验证脚本修正：rvdb使用当前history命令；GDB用break *main比较精确入口，避免源码断点跳过序言。网络DNS和本机TCP沙箱限制均经批准处理，没有计作代码修复失败。

每轮记录不同假设、修改、命令、日志和结果。三轮失败停止该问题修改，列出人工事项。网络/权限问题单列，不把未执行代码修改算作修复尝试。
