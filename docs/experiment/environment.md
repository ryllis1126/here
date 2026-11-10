# 环境配置记录

2026-11-10初始实测：

- WSL2 x86_64，内核6.18.58.1-microsoft-standard-WSL2。
- Rust `1.100.0-nightly (420ed2a0c 2026-09-18)`，Cargo `1.100.0-nightly (495c385d0 2026-09-16)`；本地nightly未改动。CI使用nightly-2026-09-01。
- `/opt/riscv/bin/riscv64-unknown-elf-gcc`：15.1.0。
- 同目录GDB启动失败，ldd：`libpython3.10.so.1.0 => not found`。
- riscv-tests已初始化，ISA ELF未构建。
- 初次沙箱DNS失败，获批联网后课程下载成功；.git和.agents为只读路径，写入通过工具请求批准。

## 修复与验收结果

- GDB通过 `bash scripts/setup-gdb.sh` 项目内解包匹配Python ABI修复。包版本3.10.12-1~22.04.18，三包SHA256固定于脚本；来源Ubuntu官方HTTPS。不修改系统配置、全局工具链或/opt。
- 当前nightly完整构建/336项测试通过。Cargo.lock纳入版本管理，以 `--locked` 复现依赖。上游已稳定feature警告保留，不影响结果。
- 13个裸机ELF强制重新编译；rv64测试套件8组覆盖238 ELF通过。
- rvdb/GDB真实会话通过；本机TCP权限通过工具批准。
- Git身份仅本仓库设置为已连接账号kaze-1126及对应GitHub noreply邮箱；origin和master推送目标不变，upstream仍禁用。

## Chapter 5 Linux工具

使用相同nightly和交叉工具链。`scripts/setup-linux.sh`在项目缓存保存校验过SHA256的官方OpenSBI v1.5.1/Linux BusyBox固件和Ubuntu dtc1.7.0包；仅dpkg-deb解包，没有安装系统包。`bash scripts/lab.sh dtc`实际编译DTB通过。WSL中`gh auth status`沙箱内外均仍显示未登录，所有推送继续暂停。
