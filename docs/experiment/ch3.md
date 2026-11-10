# Chapter 0x03：字节差分后端与参考模型

状态：后端实现、实测及独立审查通过；本地里程碑ch3，推送暂停。

## 目标、来源和方案

[课程原文](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch3/)要求为前章指令实现完整ExecTrait计算/路由，覆盖正常、边界、溢出、通道独立、x0、PC和流水依赖，并以C软件参考模型自动对照。

沿用ch2的PSUB8与PABSDIFF8定义。ExecTrait只做每个u8通道的纯计算；执行包装记录日志并复用exec_arith/normal_exec管理寄存器、PC和退休计数。Rust使用独立手算期望；C使用移位/掩码参考模型和确定性随机向量，避免与Rust字节数组算法同构。

## 计划

1. 先增加CPU后端测试：0/全1/借位隔离/高位通道/极值；源/目标x0、rd与rs1重叠；PC环绕/退休计数；连续依赖流水，观察前端占位实现失败。
2. 在exec_custom.rs实现ExecTrait并接入原路由；前端测试从“暂不写rd”更新为本章定义的真实结果，并保留PC/退休/源寄存器断言。
3. 将lab_custom.c升级为软件参考模型测试集，包含固定边界与确定性随机数据；逐例比较，失败打印输入/期望/实际，不只打印固定PASS。
4. 更新同一验证脚本检查实际计算结果与本次隔离执行日志；完整default/custom Cargo、Chapter1回归；记录、独立审查、commit/Annotated ch3。推送仍暂停。

## 命令、结果和Git

```sh
cargo test --locked --features custom-instr lab_custom_backend_tests
bash scripts/lab.sh build --features custom-instr
make -B -C test_resources -j4
python3 scripts/check-custom.py
bash scripts/lab.sh test
bash scripts/lab.sh test --features custom-instr
HERE_LAB_CHAPTER=ch3 python3 scripts/check-calculator.py
cargo fmt --all -- --check
```

## 核心代码与实际结果

- `exec_custom.rs`实现ExecPsub8/ExecPabsdiff8两个ExecTrait。按WordType全部字节独立计算，sub使用u8::wrapping_sub，绝对差使用u8::abs_diff；不使用整个64位减法，不让借位跨通道。
- 路由沿用ch2，执行包装先校验R型参数、输出backend日志，再由exec_arith读取源/写回目标；normal_exec管理PC+4与minstret+1，executor统一强制x0=0。纯数学与CPU状态分离。
- Rust新增3组测试先红后绿。覆盖0/全1、每通道0-1环绕、0x80/0x7f边界、交错通道、最高字节；rd=x0、rs1/rs2=x0、rd=rs1、无关寄存器保持；PC从0xfffffffffffffffc环绕到0，退休9->10。实际取指5条相依指令验证0xfb/0xf1/0xf6及PC+20/退休5。
- ch2阶段测试在本章明确升级为真实结果断言（0xfefe/0x0202），保留源寄存器、PC和退休验证；旧Tag仍可复现前端阶段，没有降低断言。
- 裸机C参考模型独立使用移位/掩码，与Rust字节数组实现不同。8个固定边界+8个逐通道借位+512对确定性随机输入，两条指令共1056次比较全部通过；每条指令日志528次。修复前同一程序实际报错all1-all1返回all1而非0，Python验收失败；因此不是硬编码PASS。
- `check-custom.py`在每次新的隔离运行目录检查日志、1056计数、失败标志和周期上限，返回0。脚本不把模拟器进程退出0单独视为通过：guest PowerOff会使失败分支进程也退出0，必须检查客体测试结果。
- default完整337项通过（318+10+1+8）；custom完整342项通过（323+10+1+8），0失败/0忽略。238个ISA ELF继续通过，Chapter1宿主UBSan/UART各16例和BSS热重启回归通过。
- 16个裸机示例重建通过。发现Makefile未跟踪头文件，旧版make -n错误报告up-to-date；增加-MMD/-MP和.d包含，强制编译一次建立依赖，再仅touch custom_ops.h，dry-run正确安排重编/重链，实际重编及1056对照复跑通过。无删除旧文件或清理用户数据。
- 独立审查发现新增头文件依赖会使库编译规则的$^包含多个输入，触发gcc -c/-o错误；实际复现后将该规则改为$<，只编译源文件。相同库头文件变更命令、全部重链和1056对照/前章回归再次通过；审查确认无剩余问题。

证据：[Rust先红](evidence/ch3-backend-red.txt)、[Rust转绿](evidence/ch3-backend-green.txt)、[C修复前](evidence/ch3-c-red.txt)、[C后端](evidence/ch3-custom-uart.txt)、[执行日志](evidence/ch3-custom-execution.txt)、[default回归](evidence/ch3-default-tests.txt)、[custom回归](evidence/ch3-custom-tests.txt)、[头文件依赖验证](evidence/ch3-header-dependency.txt)。

## Git与未完成项

前章Commit5f02412、Annotated ch2。本章由Annotated ch3定位，实际SHA创建后写progress.md。后端功能验收无未完成项；origin认证未解决，所有推送继续暂停。
