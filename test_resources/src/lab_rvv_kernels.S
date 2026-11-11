    .text
    .p2align 2
    .globl lab_dot
    .type lab_dot, @function
/* a0 = A, a1 = B, a2 = length. Return the low 32 bits of the dot product. */
lab_dot:
    vsetvli t0, zero, e32, m1, ta, ma
    vmv.v.i v8, 0
    beqz a2, .Lreduce
.Ldot_strip:
    /* Preserve accumulator lanes outside the final short strip. */
    vsetvli t1, a2, e32, m1, tu, ma
    vle32.v v9, (a0)
    vle32.v v10, (a1)
    vmacc.vv v8, v9, v10
    slli t2, t1, 2
    add a0, a0, t2
    add a1, a1, t2
    sub a2, a2, t1
    bnez a2, .Ldot_strip
.Lreduce:
    /* VLMAX for e32,m1 is a power of two. Keep each half-sum in-register. */
    vsetvli t0, zero, e32, m1, ta, ma
    srli t1, t0, 1
    beqz t1, .Ldot_result
.Lreduce_step:
    vslidedown.vx v11, v8, t1
    vadd.vv v8, v8, v11
    srli t1, t1, 1
    bnez t1, .Lreduce_step
.Ldot_result:
    vmv.x.s a0, v8
    ret
    .size lab_dot, .-lab_dot

    .globl lab_gemm
    .type lab_gemm, @function
/* a0 = C, a1 = A, a2 = B, a3 = M, a4 = N, a5 = K. Row-major C = A*B. */
lab_gemm:
    beqz a3, .Lgemm_done
    beqz a4, .Lgemm_done
    slli t5, a4, 2
.Lgemm_row:
    mv a6, a2
    mv t1, a4
.Lgemm_cols:
    vsetvli t0, t1, e32, m1, ta, ma
    vmv.v.i v8, 0
    mv t2, a6
    mv t3, a1
    mv t4, a5
    beqz t4, .Lgemm_store
.Lgemm_inner:
    lw t6, 0(t3)
    vle32.v v9, (t2)
    vmacc.vx v8, t6, v9
    addi t3, t3, 4
    add t2, t2, t5
    addi t4, t4, -1
    bnez t4, .Lgemm_inner
.Lgemm_store:
    vse32.v v8, (a0)
    slli t6, t0, 2
    add a0, a0, t6
    add a6, a6, t6
    sub t1, t1, t0
    bnez t1, .Lgemm_cols
    slli t6, a5, 2
    add a1, a1, t6
    addi a3, a3, -1
    bnez a3, .Lgemm_row
.Lgemm_done:
    ret
    .size lab_gemm, .-lab_gemm
