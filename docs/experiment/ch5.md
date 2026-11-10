# Chapter 0x05：VirtIO-RNG外设

状态：功能、Rust/裸机/Linux及前章回归已实测通过，独立审查通过，准备Git里程碑；推送仍受WSL认证阻塞。

## 目标与方案

[课程原文](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch5/)要求独立实现可被Linux原生驱动识别和使用的外设，涉及MMIO/注册/PLIC、按需异步后台、DMA与Acquire-Release同步。

选择VirtIO-RNG（device ID=4、单requestq），复用现有VirtIOMMIO及VirtQueue，不把已有VirtIORng枚举当实现。真实熵源为宿主/dev/urandom，后台任务通过TaskSpawner处理，队列数据及used ring写完后Release置ISR，主线程Acquire采样。Linux验证必须实际读/dev/hwrng，不能仅看设备ID。规范依据：[OASIS VirtIO entropy device](https://github.com/oasis-tcs/virtio-spec/blob/master/device-types/entropy/description.tex)，设备可以返回少于请求长度的熵，来宾必须检查used长度。

## 具体计划

- 先用公共板卡/MMIO接口写集成测试：CLI设备解析、features/队列、可写descriptor DMA、IRQ ACK/复位、只读descriptor拒写、host熵源错误；观察未实现失败。
- 新virtio_rng.rs实现设备trait及后台任务，设备builder用trait object统一block/RNG；lib.rs增加virtio-rng:PATH配置，保留block路径和现有功能。
- 后台只保留经VirtQueue验证的RAM区域；完成前不发布used/ISR，reset通过FIFO屏障等待既有任务结束，不让旧DMA跨复位。
- 新裸机程序配置split queue和PLIC，真实等待外部中断、检查used长度和两次熵数据；Linux加载DTB中的virtio节点，用原生virtio_rng驱动读/dev/hwrng。
- 添加可复用的本地dtc/官方内核准备与Linux运行入口；均项目内缓存，不安装系统包或挂载宿主磁盘。
- 运行新增Rust/裸机/Linux测试和前章回归，独立审查、记录、commit/Annotated ch5。认证恢复后再补推。

## 环境与当前证据

课程官方预编译linux-busybox-rv64gc.bin已下载并核对发布页SHA256 edd320d80d5c05175c899b9328ee11809226459271ea76eaef59efd4328c178b，约28MB。Ubuntu官方dtc 1.7.0包仅解包到.cache/tools/dtc，可实际生成DTB。

首次无VirtIO设备的Linux基线运行到晚期内核初始化，1000000000周期后达上限，尚未进入shell；没有判定Linux已启动通过。保留.cache/lab/linux-baseline.txt，后续定位熵源/初始化等待及运行预算，不能把达到上限写成成功。

## Git和未完成项

前章edbeb24/Annotated ch4。本章计划Annotated ch5，实际提交通过`git rev-parse ch5^{commit}`定位；提交创建前不填写自身SHA。Linux真实识别/读取已完成，独立审查无Critical/Important问题，Git关卡执行中。宿主熵质量依赖操作系统/dev/urandom，不把测试固定字节源当成生产随机源。

## 核心修改与原理

- `src/device/virtio/virtio_rng.rs`：异步任务接收有界请求，先暂存宿主读取结果再DMA，单请求最多4096字节。只写device-writable描述符，非法方向完成0字节且不覆盖RAM。宿主读取失败不发布部分数据，置DEVICE_NEEDS_RESET及配置中断；reset以FIFO屏障排空已提交DMA，清队列/features/ISR。
- 复用VirtIOMMIO寄存器与统一MMIO/PLIC注册；`builder.rs`通过trait object同时支持已有block及新RNG；CLI可传`--device virtio-rng:/dev/urandom`。VERSION_1是唯一功能位，没有声称支持indirect/event等扩展。
- DMA后used idx和ISR均Release发布，主线程IRQ/寄存器读取Acquire观察。后台关闭会排空有限队列，板卡TaskHandle先于RAM销毁，避免悬空DMA。
- `tests/virtio_rng.rs`通过公开板卡/MMIO接口配置完整队列，不直接调用设备内部实现。`lab_rng.c`是真实裸机驱动，配置PLIC、处理claim/ACK/complete并比较两次熵数据。
- `scripts/setup-linux.sh`校验并缓存官方固件与Ubuntu本地dtc；`lab.sh dtc`复用本地工具；所有资产均在项目缓存，没有sudo、系统包安装或宿主挂载。Linux测试自动发送回车激活BusyBox，再`mdev -s`生成字符设备。

## 编译和测试命令

```sh
bash scripts/setup-linux.sh
bash scripts/lab.sh dtc -I dts -O dtb -o dts/virt.dtb dts/virt.dts
bash scripts/lab.sh build --features custom-instr
bash scripts/lab.sh test
bash scripts/lab.sh test --features custom-instr
python3 scripts/check-rng.py
python3 scripts/check-linux-rng.py
HERE_LAB_CHAPTER=ch5 python3 scripts/check-calculator.py
HERE_LAB_CHAPTER=ch5 python3 scripts/check-custom.py
HERE_LAB_CHAPTER=ch5 python3 scripts/check-monitor.py
HERE_LAB_CHAPTER=ch5 python3 scripts/check-debuggers.py
cargo fmt --all -- --check
```

Cargo使用Cargo.lock；完整测试宿主300秒。裸机RNG宿主30秒/50000000周期，Linux宿主200秒/12000000000周期；实际均在预算内正常退出。GDB仍按已有计数stepi及宿主超时执行，不声称CLI周期限制对GDB有效。

## 实际测试结果与运行输出

- 最初4项MMIO测试均因`Unknown device type: virtio-rng`真实失败（`.cache/ch5-rng-red.log`）；实现后加上pending DMA reset回归加上分散描述符链共6项通过。保留关键先红后绿证据。
- 完整默认345项、自定义指令350项通过，0失败/0忽略；其中8个ISA测试分组覆盖原238 ELF，6项新增RNG集成测试。证据`ch5-default-tests.txt`/`ch5-custom-tests.txt`。
- 裸机：`RNG IRQ DMA PASS: requests=2 bytes=128 irq=2`，退出0；两次DMA、两次PLIC IRQ、used id/len、两份不同非零数据、reset均有真实断言。
- Linux：`rng_current=virtio_rng.0`，sysfs设备号`10:183`；`mdev -s`退出0后`/dev/hwrng`为字符设备。`dd`返回0，`wc`输出`32 /tmp/entropy`，`od`打印32字节，`HERE_RNG_PASS`后正常Power down/退出0；宿主24.82秒，无周期上限或panic。完整证据`evidence/ch5-linux-rng.txt`。
- 前章：宿主UBSan/来宾计算器各16例，BSS热重启，1056次C参考比较及528条/指令日志，monitor公平轮转/优先级/异常服务，原ecall/trap/CLINT，rvdb与RISC-V GDB会话全部通过。

## 故障分析

首次Linux基线周期预算不足，仍在内核late init；增加有界预算后到控制台激活提示，未发送回车不能进入shell，按BusyBox提示自动激活后进入shell。第一次shell检查显示原生驱动已注册但/dev节点缺失，dd明确失败（READ_STATUS=1），不是设备DMA成功；在来宾运行mdev扫描sysfs生成节点后重新启动完整验证才通过。原始失败日志分别保留`.cache/lab/linux-baseline.txt`、`linux-rng.txt`、`ch5-linux-rng-before-devnodes.txt`，没有用退出0替代功能断言。

一次回归命令将feature误写为custom-instruct，Cargo退出101；按Cargo.toml改为custom-instr后完整重跑通过，未修改测试或断言。

独立审查范围：实际/dev/urandom及有限普通测试文件；不保证任意会永久阻塞的宿主设备源。共享VirtIO transport/queue已有的恶意来宾内存安全与完整协议合规性未在本章重写；本章不宣称完整VirtIO认证。按审查建议补充双描述符散布DMA，完整345/350项重跑通过。
