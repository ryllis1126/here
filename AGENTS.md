# HERE 2026 实验工作约定

## 任务与资料

- 课程：https://heu-cs-dphd.github.io/projects/emu-exp-2026/ 。先读对应完整章节及关联资料，再核对当前源码接口；网页示例不能代替运行证据。
- 执行实验时读取 `.agents/skills/here-lab/SKILL.md`，从 `docs/experiment/README.md` 和 `progress.md` 恢复进度。
- 已有功能只是基础。每章须有个人实践、必要测试、真实输出及独立记录，不能仅因源码已有实现判定通过。
- 沿用现有模块和 Makefile；工具入口集中在 `scripts/lab.sh`，避免重复工作流。

## 开发与验证

- 在用户指定的 `master` 开发，不另建工作树或分支。改动前检查状态并保留用户改动。
- Rust 使用本地 nightly，记录完整版本；不擅自修改全局工具链。构建使用 Cargo.lock。
- 功能修改先写可重现失败的必要测试，再做最小修复；不要为机械文档改动增加无意义测试。
- 每章运行相关测试和前章回归；保留 stdout、stderr、退出码、测试数、超时和精确命令。
- `cargo test` 默认包含 riscv-tests；ISA ELF 缺失时不能跳过、删测试或降低断言。先通过 `bash scripts/lab.sh isa` 构建。
- 普通模拟器批量运行同时设置周期上限和宿主超时；调试会话同时使用宿主超时和命令步数预算（GDB用有计数的stepi，而不是无界continue）。GDB当前不消费CLI周期上限，需如实记录；达到上限不是成功，必须检查断言/输出及退出状态。
- 修改 Rust 后运行 `cargo fmt --all -- --check`；完成前检查完整 diff。
- 相同问题最多三轮有实质区别的修复，记录假设、证据和结果。三轮失败后停止该问题修改，列出人工事项，不掩盖失败。

## Git

- origin 固定为 `https://github.com/ryllis1126/here.git`；upstream 为 `https://github.com/here-emulator/here.git`，仅拉取，pushurl 保持 `DISABLED`。
- master 跟踪 origin/master，remote.pushDefault 与 branch.master.pushRemote 为 origin。
- 不重新 clone/init，不 reset --hard、git clean、force push、改写历史、删除分支/Tag 或向 upstream 推送。
- 验收通过后提交本章成果，创建 Annotated Tag：ch0（0x00.1 和 0x00.2）、ch1…ch7。已存在 Tag 不覆盖；先查本地和远程，冲突时报告。
- 用户已授权逐章 commit、Tag 和向个人 origin 推送。显式推送 master 与本章 Tag；推送失败立即停止推送并报告，不强制覆盖。
- 报告中的章节提交可用 `git rev-parse chN^{commit}` 复现，避免在提交内伪造自身 SHA；下一章/最终索引补充实际 SHA。

## 权限与安全

- 普通文件、源码、Cargo/Make、测试、模拟器运行、commit 和新 Tag 已获授权。沙箱只读/联网限制仍通过工具请求相应批准。
- sudo、apt 安装、系统配置、全局 Rust 工具链、特殊权限挂载必须先批准。优先项目内工具和不挂载的镜像操作。
- 不删除用户文件，不格式化物理磁盘。镜像脚本只接受项目明确创建的普通镜像文件，拒绝 /dev 设备。
- 不输出凭证，不代用户发送 issue、评论或其他消息，除非另有明确授权。
