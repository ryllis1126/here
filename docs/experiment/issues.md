# 问题与修复账本

| ID | 根因证据 | 实质修复轮次 | 状态 |
|---|---|---:|---|
| ENV-GDB | ldd缺libpython3.10，GDB不能启动 | 1/3 | 已解决：Ubuntu匹配ABI库项目内解包；--version和Remote会话通过 |
| ENV-ISA | riscv-tests/isa无测试ELF | 1/3 | 已解决：GNU工具链构建，8组238ELF实际通过，无新增排除 |
| CLI-NOTTY | main无条件开启rawmode，重定向运行退出2 | 1/3 | 已解决：回归先红后绿；仅TTY开启guard；完整回归通过 |

调试验证脚本修正：rvdb使用当前history命令；GDB用break *main比较精确入口，避免源码断点跳过序言。网络DNS和本机TCP沙箱限制均经批准处理，没有计作代码修复失败。

每轮记录不同假设、修改、命令、日志和结果。三轮失败停止该问题修改，列出人工事项。网络/权限问题单列，不把未执行代码修改算作修复尝试。
