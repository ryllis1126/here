# Chapter 0x01：终端计算器裸机移植

状态：实现、实测及独立审查通过；本地里程碑ch1，推送保持暂停。

## 目标、来源与方案

[课程原文](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch1/)：理解ABI、汇编、ELF、链接脚本、启动和MMIO；移植自选终端裸机程序。

选择常见的双操作数整数计算器：先用同一C源码的宿主stdio适配验证，再以HERE UART适配移植到RV64裸机。支持add/sub/mul/div、正负32位整数、帮助和退出；错误覆盖溢出、除零、格式、超长输入。计算用int64中间值避免C有符号溢出未定义行为。

## 具体计划与源码接口

- 新增 `test_resources/src/lab_calculator.c`，HOST_TEST选择stdio，裸机使用已有uart_getc/printf/PowerOff；复用Makefile和链接库。
- 先用 `scripts/check-calculator.py` 定义真实交互验收（宿主与HERE同数据），观察未实现失败，再实现。
- 读取boot.S/linker.ld/load.rs及io.c；用readelf/nm/objdump确认ELF段、入口、符号、ABI保存寄存器和栈。
- 构建并在HERE实际发送命令，逐条核对输出，不仅测试宿主；运行前章Cargo回归。
- 完成记录、diff、commit与Annotated ch1。origin认证阻塞解除前不再尝试推送。

## 实测命令、结果和核心说明

```sh
make -C test_resources -j4
python3 scripts/check-calculator.py
bash scripts/lab.sh test
HERE_LAB_CHAPTER=ch1 python3 scripts/check-debuggers.py
riscv64-unknown-elf-readelf -h -l -S test_resources/bin/lab_calculator.elf
riscv64-unknown-elf-nm -n test_resources/bin/lab_calculator.elf
riscv64-unknown-elf-objdump -d test_resources/bin/lab_calculator.elf
```

实际结果：

- 同一C计算器源码在宿主使用stdio、RV64使用已有UART库；宿主启用UBSan并对16种交互逐条核对，0错误、无UBSan诊断。
- HERE实际UART交互同样16例通过：普通/负数运算、最小有符号值、加减乘/INT_MIN除-1溢出、除零、非法整数/语法、160字节超长行；超长行排空后下一条add40 2正确返回42；quit输出BYE并通过PowerManager正常停止。不是只在宿主测试计算函数。
- 启动回归先红：将BSS写成0xdeadbeef12345678、保留.data中的重启标志，跳回_start后原boot输出STARTUP BSS FAIL。修复循环边界为startbss/endbss后输出PASS，证明真正清零BSS并保留.data，而非依赖新RAM偶然为零。
- 共15个裸机示例重新链接，构建退出0；前章完整336项Cargo测试、rvdb/GDB寄存器/内存/反汇编/步进/断点回归通过。未覆盖或改写ch0历史证据，回归记录用ch1前缀保存。

### 核心代码与ABI

- `lab_calculator.c` 将输入适配与纯解析/计算分离。输入限制96字节，过长行排空；解析先检查范围再累加；int64中间值可容纳任意两个int32的积，计算完成再检查int32结果，避免C有符号溢出。
- `boot.S` 设置sp到16字节对齐stack_top，清零BSS，再以jal ra调用main。修复前错误使用栈边界。循环按8字节写入，链接脚本给BSS首尾4KiB对齐。
- ABI：函数参数/返回值用a0–a7；ra由调用写入，非叶函数保存ra；s0等被调用者保存寄存器在栈中保存/恢复。实际read_char反汇编分配16字节栈帧，sd保存ra/s0，ld恢复后ret；调用者不能假定t/a寄存器跨调用保持。
- 字符输出/输入通过UART0x10000000及LSR轮询；退出向0x00100000写0x5555。宿主stdio不参与裸机执行。

### ELF、链接与装载实测

该ELF为64位小端RISC-V EXEC，入口0x80000000。链接脚本先排列.text.ENTRY，使_start位于RAM起点；本程序main=0x8000170c。

链接视角：.text=0x80000000、.rodata=0x80004000、.data=0x80005000、.bss=0x80006000（NOBITS，0x4088字节）、栈区从0x8000b000起，stack_top=0x8001b000。

运行视角：第一个PT_LOAD将.text/.rodata合并为RX；第二个将.data/.bss合并为RW，filesz=0x10、memsz=0x5088。调试节与符号表服务静态工具，不作为程序段加载；BSS在文件中不占等量数据。

当前源码与教程差异：`ELFLoader::load_to_ram`使用PT_LOAD的virtual_addr拷贝filesz；并未单独按memsz清零或设置e_entry，初始RAM在Ram::new中为零，初始PC由板卡默认配置决定。本程序刻意令vaddr=paddr=默认PC起点，并由修正后的boot显式清BSS。未把教程描述的更完整通用ELF装载能力冒称当前实现。

证据：[真实UART](evidence/ch1-calculator-uart.txt)、[宿主](evidence/ch1-host.txt)、[BSS修复前](evidence/ch1-startup-red.txt)、[修复后](evidence/ch1-startup.txt)、[ELF分析](evidence/ch1-elf-analysis.txt)、[Cargo回归](evidence/ch1-cargo-tests.txt)、[rvdb回归](evidence/ch1-rvdb.txt)、[GDB回归](evidence/ch1-gdb.txt)。

## Git与未完成项

本章提交由Annotated `ch1`定位：`git rev-parse 'ch1^{commit}'`，实际SHA创建后写入progress.md。功能验收无未完成项；外部交付仍因origin HTTPS缺凭据而未推送，未重试推送。
