---
name: here-lab
description: Use when implementing or resuming the HEU 2026 HERE RISC-V emulator labs, validating a chapter, or preparing its experiment record and Git milestone.
---

# HERE 实验执行

先读根目录 AGENTS.md、docs/experiment/README.md、progress.md，检查工作区、分支、远程和已有 Tag。用户已指定 master 自主开发及逐章推送，不重复索要普通实施许可。

## 每章循环

1. 读取课程完整章节、关联示例与相关规范；原网页缓存放 .cache/course/，来源和摘要放 docs/experiment/requirements.md。核对实际源码，不沿用过时 API。
2. 在章节记录中写具体计划、依赖、验收条件和将触及的模块。已有功能不等于个人实验通过。
3. 通过 bash scripts/lab.sh env|build|isa|test|run 复用工具；必要功能先复现失败，再实现和验证。记录实测命令、退出码和日志路径。
4. 完成本章测试、模拟器实践和之前章节回归。Rust、ISA、裸机、GDB、Linux 等不同层级分别验收，不以某层通过代替其他层。
5. 按 docs/experiment/requirements.md 核对所有必做项，记录未完成项；无证据项保持未验收。0x00.1 和 0x00.2 共同通过才可打 ch0。
6. 检查 diff 和格式，完成章节 Markdown 记录。检查本地和远程 Tag；仅在通过后 commit、创建新 Annotated Tag，并显式推送 origin master 和该 Tag。推送失败停止推送并报告。
7. 更新 progress.md 和章节索引，继续下一章；遇到阻塞时继续独立工作，不能把依赖阻塞的章节标成通过。

## 故障记录

每个问题最多三轮不同修复假设，完整日志放 docs/experiment/evidence/（适量文本）或 .cache/lab/（大型原始输出）。三轮失败后在 issues.md 记原因、尝试、代码状态和所需人工行动，停止该问题修改。禁止删测试、弱化断言、伪造结果或用跳过测试冒充通过。

## 报告字段

每章包含目标、课程来源、方案、核心修改与原理、编译命令、测试命令与真实结果、运行输出、Git commit/Tag 定位、未完成事项。提交 SHA 用后续索引记录，章节内可引用 chN^{commit}，不填写猜测值。

向量实验只用当前支持的整数 RVV 指令；Linux 使用正确 OpenSBI/kernel 镜像与 DTB，不能把 virtio_blk_test.elf 当内核；Linux 用户程序使用 Linux ABI，不把 newlib 裸机 ELF 当 Linux 程序。
