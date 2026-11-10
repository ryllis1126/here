# Chapter 0x00.1：环境与构建

状态：实际验收通过；与0x00.2共同形成ch0里程碑。

## 目标、来源和方案

[课程原文](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch0.1/)要求nightly、交叉工具链、HERE和裸机demo、riscv-tests及Cargo测试；用户另要求GDB依赖修复。统一复现入口 `bash scripts/lab.sh`；保留全局工具链，优先本地依赖；ISA只构建不安装到/opt。

## 计划及验收

- [x] 环境版本和错误实测。
- [x] GDB依赖修复，--version运行。
- [x] HERE release重建，确定nightly兼容。
- [x] 全部13个裸机示例重建；main运行成功。
- [x] ISA ELF构建，8组测试覆盖238个ELF，各组非空。
- [x] 完整 `cargo test --features riscv-tests` 通过。

## 核心修改、命令与实际结果

1. `bash scripts/lab.sh env` 初次退出1：GDB缺少libpython3.10、ISA ELF缺失，两个问题均复现。
2. `bash scripts/setup-gdb.sh` 从Ubuntu官方源下载三份Python 3.10 ABI包，校验SHA256后仅解包到 `.cache/tools/libpython`；wrapper设置LD_LIBRARY_PATH/PYTHONHOME。GDB 16.3.90.20250610-git启动成功。不修改系统库、不使用跨版本so链接。
3. `bash scripts/lab.sh isa` 构建当前集成套件所需RV64组，含p/v。最初完整ISA构建额外生成的hypervisor二进制移至缓存，autoconf重新生成的configure恢复为开始时内容；子模块源码和引用不变。最终脚本直接调用已签入Makefile，避免生成源码变更。
4. `bash scripts/lab.sh build` 重新编译release。`make -B -C test_resources -j4` 强制重编全部13个示例，无错误。当前nightly兼容，存在上游unsafe_cell_access已稳定及manifest未用依赖警告，未为消除警告改变CI旧nightly兼容性。
5. 批量运行最初退出2：main在非TTY下仍调用enable_raw_mode。新增 `tests/cli_nonterminal.rs` 使用真实16字节poweroff机器码复现失败，再将guard限制为stdin/stdout均为TTY；测试转绿。没有模拟终端或删断言来绕过错误。
6. `bash scripts/lab.sh run test_resources/bin/main.elf` 退出0，实际输出段地址、格式化样例和PASS，并正常通过PowerManager停止。
7. `cargo test --locked --features riscv-tests` 退出0：317库测试、10 CLI单元测试、1新回归、8 ISA组全部通过，0失败/0忽略。ISA实际选择238个ELF。沿用上游已有ma_data/pmpaddr/sbreak等排除规则，没有新增排除。
8. `cargo fmt --all -- --check`、脚本语法检查、技能quick_validate退出0。

关键证据：[环境](evidence/ch0-environment.txt)、[完整Cargo测试](evidence/ch0-cargo-tests.txt)、[裸机运行](evidence/ch0-main.txt)、[编译](evidence/ch0-build.txt)、[非TTY修复前后](evidence/ch0-cli-regression.txt)。

## Git和未完成项

提交定位：`git rev-parse 'ch0^{commit}'`；Tag：Annotated `ch0`。最终实际SHA及远程状态见progress.md，未创建前不猜测SHA。

未完成项：本节无。警告如上保留。0x00.2另行记录真实调试会话。
