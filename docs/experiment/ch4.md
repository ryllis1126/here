# Chapter 0x04：M-mode monitor与U-mode任务

状态：实现、实际验收及独立审查通过；本地里程碑ch4，推送暂停。

## 目标与来源

[课程原文](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch4/)要求M->U启动、多个任务、统一ecall服务、非ecall异常的mcause/mepc/mtval验证与恢复，以及CLINT公平时间片。优先级抢占为课程扩展，本次也实施并单列验收。

## 方案和具体计划

- 复用当前TrapContext及trap.S的固定M栈帧，在强trap_handler中保存当前任务、处理服务、选择任务，再将下一上下文拷回同一帧并mret；不在任意任务结构体地址上假装内核栈帧。
- 新增lab_monitor.c与独立验收脚本；用户任务只用ecall请求putchar/sleep/spawn/exit/yield/check等服务。任务ID/寄存器sentinel和CSR断言由monitor检查，避免只打印成功文本。
- 先以真实U任务验证完整寄存器上下文（特别是原trap.S未保存的tp）以及mcause=8，观察必要回归失败后最小修复保存/恢复。
- 构造明确的32位非法指令与标号，验证mcause=2、mepc和mtval；分别演示跳过指令、终止任务及中断返回原PC。
- CLINT时间片在同优先级任务中轮转，sleep任务不就绪；无就绪任务时使用M-mode idle上下文和WFI等待最近唤醒时刻，避免monitor内忙轮询。
- 进阶：高优先级任务由低优先级任务spawn后立即抢占，同优先级公平轮转；用调度轨迹和guest内部断言验收，而非口头声称。
- 新代码、示例与完整default/custom及前章C/UART回归，整理记录后commit/Annotated ch4。origin认证恢复前不重试推送。

## 已知源码接口约束

- 原trap.S跳过tp(x4)，不足以支持完整多任务上下文，需要真实回归后修复。
- HERE当前WFI执行器等价nop；guest会发出WFI而非软件忙轮询，但宿主执行节能效果不能冒称已实现。
- 当前无PMP隔离实现，本章验证特权级与trap机制，不把U-mode简单切换冒充完整内存安全隔离。

## 命令、实际结果和Git

```sh
make -C test_resources -j4
python3 scripts/check-monitor.py
bash scripts/lab.sh test
bash scripts/lab.sh test --features custom-instr
python3 scripts/check-custom.py
HERE_LAB_CHAPTER=ch4 python3 scripts/check-calculator.py
```

## 核心实现与实际结果

- 新增lab_monitor.c，4个U任务各有8KiB栈和独立TrapContext；两个同优先级整数任务、动态spawn的高优先级任务、异常测试任务。另有M-mode idle上下文，M trap栈16KiB。固定测试任务集，不宣称支持任意ELF动态装载。
- syscall使用a7服务号/a0参数和返回值，提供putchar、sleep ticks、spawn、exit、yield、用户断言和读取时间。该教学ABI不是标准SBI；已阅读[SBI二进制调用约定](https://github.com/riscv-non-isa/riscv-sbi-doc/blob/master/src/binary-encoding.adoc)，标准SBI的S->M/EID/FID与本章U->M服务有明确区别。
- 真实U任务读tp并调用断言服务，原trap.S未恢复tp使初次运行报MONITOR FAIL。最小修复为入口保存x0和tp、返回恢复tp；同一任务验证转绿。所有通用寄存器、mstatus、mepc由同一272字节固定栈帧保存，内核拷贝任务上下文后mret。
- ecall实测mcause=8、mtval=0、保存MPP=U，mepc指向实际0x73指令；处理后PC+4。普通指令流被定时器打断时保持原mepc，不像ecall那样加4，工作任务累计sum=199990000检查跨抢占上下文正确。
- 非法指令0xfff00073在精确符号lab_fault_skip处产生mcause=2，mtval匹配；跳过4字节后继续到用户断言。随后U任务执行mstatus CSR读取0x30002573，再次mcause=2，精确mepc/mtval匹配，monitor终止该任务，其他任务继续。若误在M-mode运行，该CSR读取不会报同样错误，因此也验证了特权切换。
- 验收脚本通过nm独立取得两个故障标号，比较真实CSR输出，不依赖硬编码链接地址；检查调度轨迹中spawn后的0->2、定时唤醒后的低优先级->2、0<->1的双向timer轮转以及idle进入/唤醒。
- CLINT按mtime/mtimecmp工作，时钟实际为模拟器周期数>>3，每个时间片4096 tick。两个普通任务分别获得7/8次定时器打断，14次双向公平切换；优先级2任务就绪时优先于优先级1；同优先级按round-robin。worker在spawn返回后检查高优先级子任务确已执行。
- sleep把任务移出READY集合，记录唤醒时刻；无就绪任务时进入M idle，并把CLINT设为最近唤醒时刻。实测idle进入2次、睡眠唤醒3次；用户检查sleep前后时间差达到请求值；执行yield后其他任务可运行。程序没有在monitor内部轮询等待mtime。
- 主测试进程退出0、MONITOR PASS；17个裸机示例构建通过；现有ecall_test、trap_test、clint均真实输出PASS；default339项和custom344项（含238 ISA ELF）全部通过、0忽略。前章1056次C对照和host/UART16例及BSS热重启回归通过。

证据：[tp修复前](evidence/ch4-context-red.txt)、[Monitor完整运行与调度](evidence/ch4-monitor.txt)、[default测试](evidence/ch4-default-tests.txt)、[custom测试](evidence/ch4-custom-tests.txt)、[现有ecall](evidence/ch4-regression-ecall_test.txt)、[现有异常](evidence/ch4-regression-trap_test.txt)、[CLINT](evidence/ch4-regression-clint.txt)。

## Git与未完成项

本章以Annotated ch4定位（创建后 `git rev-parse 'ch4^{commit}'`），实际SHA后续写progress.md；Chapter3补充为fa18065/ch3-fix1，原65b5a51/ch3保留已知竞态记录。

本章必做及优先级抢占扩展已实测完成。可中断I/O睡眠属于课程可选探索，未实现，不冒称已完成；WFI的宿主节能与PMP隔离限制如前。origin仍因WSL未登录而暂停推送。
