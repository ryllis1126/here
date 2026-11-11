# Chapter 0x06：Linux 系统整合

OpenSBI 引导、BusyBox 磁盘程序、Alpine Ext4 根文件系统和来宾原生编译均已在 HERE 实测通过。前章为 dc36f42（ch5）。课程依据为 [Chapter 0x06](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch6/)。

## 启动链路与实现

- OpenSBI 1.5.1 将控制权交给 0x80200000 的 S-mode Linux 6.18.2，DTB 地址为 0x9f000000。
- linux-lab.dts 将 VirtIO Block 配置在 0x10001000，使用 IRQ 1。RNG 位于 0x10002000，使用 IRQ 2。CLI 设备顺序与 DTB 一致。
- prepare-linux.py 用 Clang 22.1.7、RISC-V musl CRT、libc 和 libgcc，将第 1 章计算器构建为 RV64GC Linux ABI 静态 ELF。40 MiB 镜像通过 mkfs.ext4 -d 导入程序。
- 课程发布包内置 BusyBox initramfs。直接让内核挂载磁盘时，该 initramfs 缺少 /root，内核返回 ENOENT。Alpine DTB 令 /bin/sh 作为早期 PID 1，由它加载设备节点、挂载 /dev/vda，再以 BusyBox switch_root 执行 Alpine 的 /sbin/init。来宾 /proc/mounts 记录 /dev/vda / ext4 rw。[Linux 内核文档](https://www.kernel.org/doc/html/latest/admin-guide/initrd.html)
- Alpine 3.24.4 的 512 MiB 镜像包含 SHA-256 清单列出的官方 RISC-V APK。来宾执行 apk --no-network add /opt/apks/*.apk，安装后原生编译。
- lab-image.py 以独占创建方式预留镜像。创建、验证与读回使用普通镜像文件，宿主无需挂载。

## 复现

    bash scripts/lab.sh build --features custom-instr
    bash scripts/lab.sh linux-prepare --busybox-image busybox-repro.img --alpine-image alpine-repro.img
    HERE_BUSYBOX_IMAGE=busybox-repro.img python3 scripts/check-linux-disk.py
    HERE_ALPINE_IMAGE=alpine-repro.img python3 scripts/check-alpine.py
    python3 tests/test_lab_image.py
    bash scripts/lab.sh test
    bash scripts/lab.sh test --features custom-instr

每次准备镜像使用新的文件名。验收使用 busybox-ch6-final.img 和 alpine-ch6-final.img。[准备日志](evidence/ch6-final-prepare.txt)

| 验收项 | 实测结果 | 证据 |
|---|---|---|
| BusyBox 挂载和程序运行 | 6 项计算用例通过，挂载、程序、写入、卸载均返回 0 | [串口](evidence/ch6-linux-disk.txt) |
| 磁盘持久化 | 关机后 debugfs 读回本次唯一标记，e2fsck 退出 0 | [写入](evidence/ch6-disk-persistence.txt)、[检查](evidence/ch6-e2fsck.txt) |
| Alpine 根与开发环境 | Ext4 磁盘根，APK 安装或更新 16 个包，GCC 15.2.0、Make 4.4.1 | [串口](evidence/ch6-final-alpine.txt) |
| 来宾原生编译与执行 | 编译和执行返回 0，输出 ALPINE GCC PASS: 42，正常关机 | [串口](evidence/ch6-final-alpine.txt) |
| 镜像安全及块 I/O | 安全测试 3 项通过，4 MiB 读取回归先失败后通过 | [安全](evidence/ch6-image-green.txt)、[修复前](evidence/ch6-block-read-red.txt)、[修复后](evidence/ch6-block-read-green.txt) |
| 全量 Rust 与 ISA | 默认 346 项、自定义指令 351 项通过，均 0 失败、0 忽略，含 8 组 ISA | [默认](evidence/ch6-default-tests.txt)、[自定义](evidence/ch6-custom-tests.txt) |

BusyBox 宿主上限 240 秒、模拟 160 亿周期。Alpine 宿主上限 600 秒、模拟 400 亿周期。最终 Alpine 安装、编译和关机耗时约 246 秒。前章计算器、BSS、1056 次自定义指令对照、M-mode monitor、RNG 和 rvdb/GDB 均已回归，证据在 evidence/ch6-*.txt。

## 故障与交付

第一次切根失败日志在 .cache/lab/ch6-alpine-before-root.txt，根目录检查见 [诊断](evidence/ch6-root-diagnostic.txt)。切根后，大段 APK 读取暴露 VirtIO Block 将异步短读当作错误的问题。4 MiB MMIO 测试复现 IOERR。修复按实际返回字节数累进，填满段后继续，EOF 或真实读取错误仍报告为 I/O 错误。修复前来宾部分输出在 .cache/lab/ch6-alpine-short-read-partial.txt。

Buildroot 可按配置构建定制系统镜像，Debian 提供发行版包生态。两者作为资料探索，实际部署的发行版为 Alpine。[Buildroot 手册](https://buildroot.org/downloads/manual/manual.html) · [Debian RISC-V 移植](https://wiki.debian.org/RISC-V)

本章提交通过 git rev-parse ch6^{commit} 定位。origin 推送等待 WSL GitHub HTTPS 凭据。
