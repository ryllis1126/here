# Chapter 0x07：整数向量与矩阵

完成个人 RVV 点积、整数 GEMM、Clang 自动向量化和标量对照。前章提交为 d722353（ch6）。[课程第 7 章](https://heu-cs-dphd.github.io/projects/emu-exp-2026/ch7/)

## 实现

- HERE 当前 VLEN=128。点积采用 e32,m1，按运行时 VL 步进，借助 vmacc.vv 乘加。短条带使用尾部保持策略，以保留累计结果。最后在寄存器内用 vslidedown.vx 和 vadd.vv 做树形规约，通过 vmv.x.s 返回。矩阵算子按输出行和列条带遍历，使用连续 B 行片段与 A 标量执行 vmacc.vx。
- 算术按 32 位低位环绕定义。标量参考用 uint32_t 表达相同位模式，避免 C 有符号溢出的未定义行为。乘积和求和取低 32 位时，有符号与无符号输入的位结果一致。
- AXPY 源码为普通 C 循环。Clang 22.1.7 在 -O3 下报告 vscale × 4 的向量化宽度。最终 ELF 包含 e32,m2 的 vsetvli、vle32.v、vmacc.vx 和 vse32.v，非空输入经过向量循环。关闭 Loop 和 SLP 向量化的同源对象反汇编仅有标量指令。LLVM 通过 scalable vector 类型表示运行时宽度，后端按 SEW、LMUL 和 AVL 插入配置。[LLVM RVV 文档](https://llvm.org/docs/RISCV/RISCVVectorExtension.html)
- P 草案在通用寄存器中打包小整数。AME 任务组讨论独立矩阵寄存器和矩阵运算。实验算子使用 HERE 当前支持的整数 RVV 指令。[P 草案](https://github.com/riscv/riscv-p-spec) · [AME 任务组资料](https://lists.riscv.org/g/tech-attached-matrix-extension/attachment/310/0/AME-20250414.pdf)

## AVL 故障

点积首跑在长度 0 报错，并达到周期上限。Rust 回归确认 vsetvli 的 x0 源操作数走了普通寄存器读取路径，使 VL 从应有的 4 变为 0。修复对 vsetvli 和 vsetvl 按寄存器字段解释 AVL。rs1=x0 且 rd 非零时请求 VLMAX，两者皆为 x0 时以当前 VL 为 AVL，其余使用源寄存器值。vsetivli 保持立即数语义。回归覆盖两种寄存器指令的三类 AVL，随后同一裸机程序通过。[RVV 规范 AVL 编码](https://github.com/riscvarchive/riscv-v-spec/blob/master/v-spec.adoc#62-avl-encoding)

## 复现和实际结果

    bash scripts/lab.sh build --features custom-instr
    bash scripts/lab.sh rvv
    bash scripts/lab.sh test vector_op
    bash scripts/lab.sh test
    bash scripts/lab.sh test --features custom-instr
    cargo fmt --all -- --check

| 验收项 | 实测结果 | 证据 |
|---|---|---|
| 点积及编译器 AXPY | 各 14 个长度，涵盖 0、1、VL 边界、非整条带和 257，标量对照一致 | [串口](evidence/ch7-rvv-uart.txt) |
| 整数 GEMM | 7 个形状，含方阵、长矩形、尾列和零维，逐元素一致且保护值保留 | [串口](evidence/ch7-rvv-uart.txt)、[反汇编](evidence/ch7-lab_gemm.txt) |
| Clang 生成 | 优化备注、RVV 反汇编和关闭向量化的标量反汇编 | [优化备注](evidence/ch7-build.txt)、[RVV](evidence/ch7-lab_axpy.txt)、[标量](evidence/ch7-scalar-disassembly.txt) |
| AVL 回归 | Rust 断言从 VL=0 失败变为通过 | [修复前](evidence/ch7-avl-red.txt)、[修复后](evidence/ch7-avl-green.txt) |
| 原向量套件 | vector_op 66 项通过，原裸机 vector_kernels 通过 | [Rust](evidence/ch7-vector-tests.txt)、[串口](evidence/ch7-upstream-vector-uart.txt) |
| 全套回归 | 默认 347 项、自定义指令 352 项，0 失败、0 忽略，含 8 组 ISA | [默认](evidence/ch7-default-tests.txt)、[自定义](evidence/ch7-custom-tests.txt) |

向量裸机运行上限为宿主 60 秒和模拟 500 万周期，两个 ELF 都输出成功标记并正常退出。前章计算器、BSS、自定义指令、特权级与定时器、裸机和 Linux RNG、rvdb/GDB、BusyBox 磁盘、Alpine Ext4 根及原生编译均已回归。完整命令、退出码和输出见 evidence/ch7-*.txt。

## 范围和交付

点积条带根据 VL 自适应，实测硬件参数为 HERE 的 VLEN=128。本章验证运算和编译器生成，未测量真实硬件速度。审查验证了 AVL、模运算和尾部处理。根据审查结果，Clang 向量化编译由 rvv 入口单独触发，默认裸机构建继续使用原工具链。提交通过 git rev-parse ch7^{commit} 定位。GitHub 推送等待 WSL HTTPS 凭据。
