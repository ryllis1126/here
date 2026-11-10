# Chapter 0x02：字节差分自定义指令前端

状态：前端阶段实现、实测与独立审查通过；本地里程碑ch2，推送暂停。

## 目标与方案

[课程原文](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch2/)要求自选指令组的编码/JSON/代码生成/译码/执行响应日志、Rust测试与C .insn封装。

面向像素/采样差分设计两条RV64 R型指令，全部8个字节通道独立：

| 指令 | 规划语义（Chapter3实现） | opcode/funct3/funct7 | match/mask |
|---|---|---|---|
| psub8 | 各通道(a-b) mod256，借位不串扰 | 0x0b/2/0 | 0x200b/0xfe00707f |
| pabsdiff8 | 各通道无符号绝对差abs(a-b) | 0x0b/3/0 | 0x300b/0xfe00707f |

已有MY_INSTR0_R占用funct3=0，本组避开它，保留官方示例。rd/rs1/rs2位置遵循标准R型；不声称它们是已批准的标准P扩展指令。

## 计划与实际源码

1. 先在decoder_test.rs写实际32位机器码的译码、操作数字段和临近非法编码测试，并在cpu_test.rs验证前端响应PC/退休。
2. 添加JSON描述，复用build.rs已具备的custom-instr条件生成；不重复写生成器或修改生成产物。
3. 新增条件编译exec_custom模块，在路由中响应并记录具体指令/寄存器；本章故意只确认前端到执行接口，计算结果留待ch3。
4. C header封装.insn r，新增lab_custom裸机探针，真实运行并读取emulator文件日志核对两条指令。
5. 完整default/custom Cargo回归、Chapter1 UART及BSS回归，检查diff和记录，commit/Annotated ch2。origin仍暂停推送。

## 实际结果、Git与未完成事项

## 编译与实测命令

```sh
cargo test --locked --features custom-instr test_lab_custom
bash scripts/lab.sh build --features custom-instr
python3 scripts/check-custom.py
bash scripts/lab.sh test
bash scripts/lab.sh test --features custom-instr
HERE_LAB_CHAPTER=ch2 python3 scripts/check-calculator.py
cargo fmt --all -- --check
```

## 实际结果与关键说明

- 新增译码与CPU执行接口测试先运行失败：两条编码均无法译码。JSON及路由实现后两项转绿；未通过放宽断言解决。
- Decoder测试使用手算机器码0x0020a18b/0x0020b18b和寄存器极值编码，核对具体指令、R型字段和4字节长度；临近未分配funct3及错误funct7仍非法。default构建中两条指令不能译码。
- JSON的32位encoding与mask/match逐位一致，检查与现有custom条目无冲突；已有my_instr0_r和display保留。生成器自动生成PSUB8/PABSDIFF8及TABLE_RVCUSTOM0，Decoder在feature启用时加载，未修改生成文件。
- 条件编译模块exec_custom记录指令名及rd/rs1/rs2，并用normal_exec正确推进PC和minstret。单测核对源寄存器未变、rd暂未写回、PC+4、退休+1；这正是本章阶段性接口，不是完整算术实现。
- C .insn header调用在HERE真实执行。独立运行目录产生的新日志中两条指令各出现一次，均记录rd=15、rs1=15、rs2=14；裸机输出CUSTOM FRONTEND PASS，正常退出0，15360周期，未达上限。
- default完整337项通过：318库+10CLI+1非TTY+8ISA组；custom完整339项通过：320库+10+1+8，均0失败/0忽略。原先忽略的display示例测试已启用，并增加PC和minstret断言，没有删除或跳过测试。
- Chapter1宿主UBSan/UART16例与热重启BSS回归通过。记录使用章节前缀，保留历史证据。

### 资料与源码链路

已阅读[汇编手册.insn说明](https://github.com/riscv-non-isa/riscv-asm-manual/blob/main/src/asm-manual.adoc)和[riscv-opcodes元数据生成说明](https://github.com/riscv/riscv-opcodes/blob/master/README.md)，以及课程列出的本仓库JSON/build/decoder/executor/cpu_tester代码；原资料缓存不提交。

从现有addi路径跟踪：build.rs根据variable_fields推导R/I等格式并生成枚举/描述表；Decoder先压缩分流，再funct快速表/必要时mask兜底，提取操作数字段。executor的step_impl先检查iCache，未命中时ifetch/decode/put，再调用execute；execute经get_exec_func路由并在返回时强制x0=0。新指令复用这条链路，无需复制CPU循环。

证据：[前端先红](evidence/ch2-front-red.txt)、[转绿](evidence/ch2-front-green.txt)、[真实UART](evidence/ch2-custom-uart.txt)、[执行日志](evidence/ch2-custom-execution.txt)、[default完整回归](evidence/ch2-default-tests.txt)、[custom完整回归](evidence/ch2-custom-tests.txt)。

## Git与未完成项

前章Commit02d8f9c、Annotated ch1；本章由Annotated ch2定位，实际SHA创建后记录于progress.md。origin认证阻塞，所有推送继续暂停。

本章前端验收无未完成项；完整算术语义、边界和C参考模型是Chapter3任务，不将日志响应冒充后端正确性。
