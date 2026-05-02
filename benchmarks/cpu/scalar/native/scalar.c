/*
 * Tiny scalar microbenchmark: integer, FP, and (optionally) NEON SIMD loops.
 *
 * Run with: ./scalar [iterations]
 * Prints one JSON line per kernel:
 *   {"kernel":"int64_add", "ops":4000000000, "seconds":0.42, "ops_per_second":9.5e9}
 *
 * Compile (Apple Silicon):
 *   clang -O3 -march=armv8.4-a+simd scalar.c -o scalar
 *
 * Compile (x86):
 *   clang -O3 -march=native scalar.c -o scalar
 *
 * The kernels are small on purpose. They measure raw issue rate of one core's
 * functional units, not memory subsystem behavior. Cross-check against STREAM
 * (memory) and sysbench (mixed) for a fuller picture.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#if defined(__ARM_NEON)
#include <arm_neon.h>
#endif

static double now_s(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static void print_kernel(const char *name, double seconds, double ops) {
    printf("{\"kernel\":\"%s\", \"ops\":%.0f, \"seconds\":%.6f, \"ops_per_second\":%.3e}\n",
           name, ops, seconds, ops / seconds);
}

static volatile uint64_t sink_u64 = 0;
static volatile double sink_d = 0.0;

static void bench_int64_add(uint64_t iters) {
    uint64_t a = 1, b = 3, c = 5, d = 7;
    double t0 = now_s();
    for (uint64_t i = 0; i < iters; i++) {
        a += b;
        c += d;
        b ^= a;
        d ^= c;
    }
    double t1 = now_s();
    sink_u64 = a + b + c + d;
    print_kernel("int64_add", t1 - t0, (double)iters * 4.0);
}

static void bench_fp64_fma(uint64_t iters) {
    double a = 1.0, b = 1.0000001, c = 0.0;
    double t0 = now_s();
    for (uint64_t i = 0; i < iters; i++) {
        c = a * b + c;
        a = a * 1.0000001 + 1.0;
        b = b * 0.9999999 + 1.0;
    }
    double t1 = now_s();
    sink_d = a + b + c;
    print_kernel("fp64_fma", t1 - t0, (double)iters * 3.0);
}

#if defined(__ARM_NEON)
static void bench_neon_fp32x4_fma(uint64_t iters) {
    float32x4_t a = vdupq_n_f32(1.0f);
    float32x4_t b = vdupq_n_f32(1.0000001f);
    float32x4_t c = vdupq_n_f32(0.0f);
    double t0 = now_s();
    for (uint64_t i = 0; i < iters; i++) {
        c = vfmaq_f32(c, a, b);
        a = vfmaq_f32(a, b, c);
        b = vfmaq_f32(b, a, c);
    }
    double t1 = now_s();
    float buf[4];
    vst1q_f32(buf, c);
    sink_d = buf[0] + buf[1] + buf[2] + buf[3];
    /* 4 lanes * 2 ops/fma * 3 fmas per iteration */
    print_kernel("neon_fp32x4_fma", t1 - t0, (double)iters * 4.0 * 2.0 * 3.0);
}
#endif

int main(int argc, char **argv) {
    uint64_t iters = (argc > 1) ? strtoull(argv[1], NULL, 10) : 1000000000ULL;
    bench_int64_add(iters);
    bench_fp64_fma(iters);
#if defined(__ARM_NEON)
    bench_neon_fp32x4_fma(iters / 4);
#endif
    return 0;
}
