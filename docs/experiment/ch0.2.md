# Chapter 0x00.2：真实调试器会话

状态：实测验收通过。

## 目标与来源

[课程原文](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch0.2/)要求掌握rvdb、寄存器/内存/反汇编/步进/断点和GDB Remote。使用当前源码的命令及TCP 127.0.0.1:1234。

## 方案、源码与核心修改

读取 `src/rvdb/{mod,commands,session,printer}.rs`、`src/gdb/{mod,eventloop}.rs` 和 `src/main.rs`。复用0x00.1非TTY rawmode修复；不修改调试器功能。

`scripts/ch0.rvdb` 为可重放命令；`scripts/check-debuggers.py` 运行真实HERE，检查命令输出和GDB对寄存器的精确断言，保存客户端与服务端完整记录。GDB监听就绪后才连接，失败/超时回收自己启动的进程。

## 编译与测试命令

```sh
bash scripts/lab.sh build
python3 scripts/check-debuggers.py
cargo test --locked --features riscv-tests
```

运行本机TCP会话需要沙箱网络批准；不需要sudo、系统配置或全局工具链变更。

执行边界：rvdb继续运行限制100000步；GDB用stepi 40000在预算内推进并由main断点提前停止，客户端整体限制宿主30秒。当前GDB模式不消费CLI的--max-cycles，因此没有使用无效CLI参数冒充预算。

## 实际结果

- rvdb：初始PC=0x80000000，读取sp和x0–x7，读取前16字节，与ELF指令一致；list正确反汇编_start。
- 步进后PC=0x80000004；设置main断点，continue 32775步后命中0x800010f0；sp=0x8001a000；删除断点并步进到0x800010f4；history显示真实执行记录。
- GDB：从匹配ABI的RISC-V GDB连接127.0.0.1:1234成功，读取pc/sp/a0、内存和反汇编；stepi后PC=0x80000004；`break *main`命中精确入口，`AT_MAIN=1`；detach后服务端退出0。
- 验证脚本退出0；完整Cargo回归336项通过（详情见0x00.1）。

当前接口差异：课程简称h在本版本不被接受，使用history；GDB的break main默认停在序言后的首个源码行，精确入口验收需break *main。这是调试命令语义差别，没有放宽地址断言。

证据：[rvdb](evidence/ch0-rvdb.txt)、[GDB客户端](evidence/ch0-gdb.txt)、[GDB服务端](evidence/ch0-gdb-server.txt)。

## Git与未完成事项

与0x00.1共同提交和Annotated Tag `ch0`，提交定位 `ch0^{commit}`；实际SHA/推送状态见progress.md。本节无未完成项。
