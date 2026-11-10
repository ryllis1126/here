# HEU 2026 HERE 实验

课程：[RISC-V Emulator 实验指导（2026）](https://heu-cs-dphd.github.io/projects/emu-exp-2026/)。基础 HEAD：`7cd34e277692c5fe6c5a9959b3206e0cff0808ff`。本目录记录个人实现与实际运行，官方已有功能不自动算作完成。

- [课程验收映射](requirements.md)
- [实施计划](plan.md)
- [持续进度](progress.md)
- [环境与工具链](environment.md)
- [问题及修复轮次](issues.md)
- [Chapter 0x00.1](ch0.1.md)
- [Chapter 0x00.2](ch0.2.md)
- [Chapter 0x01](ch1.md)
- [Chapter 0x02](ch2.md)

统一入口（项目根目录）：

```sh
bash scripts/lab.sh env
bash scripts/lab.sh build
bash scripts/lab.sh isa
bash scripts/lab.sh test
bash scripts/lab.sh run test_resources/bin/main.elf
```

原始日志 `.cache/lab/`；验收关键证据 `evidence/`。超时、失败、未运行如实记录。0x00.1 和 0x00.2 均验收后才创建 ch0，此后依次 ch1…ch7。

签入的终端文本证据仅统一换行和去掉行尾空白；输出内容、测试数和退出状态不变，大型原始日志留在缓存。
