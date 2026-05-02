/*
 * Pointer-chase memory latency benchmark.
 *
 * Allocates a working set of size N, fills it with a random permutation of
 * indices so successive loads cannot be prefetched, and times M chained
 * dependent loads. Output is one JSON line per working-set size:
 *   {"bytes":4096, "ns_per_access":1.05, "iterations":40000000}
 *
 * Sweep N from a few KB to several GB to map the L1 → L2 → SLC → DRAM
 * hierarchy.
 *
 * Compile (Apple Silicon):
 *   clang -O3 -march=armv8.4-a pointer_chase.c -o pointer_chase
 *
 * Compile (x86):
 *   clang -O3 -march=native pointer_chase.c -o pointer_chase
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static double now_s(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* Fisher-Yates shuffle of indices [0, n) into a single linked-list cycle. */
static void build_cycle(size_t *cells, size_t n) {
    for (size_t i = 0; i < n; i++) cells[i] = i;
    /* shuffle 1..n-1 (keep cells[0] as-is) */
    for (size_t i = n - 1; i > 1; i--) {
        size_t j = 1 + (size_t)((double)rand() / ((double)RAND_MAX + 1.0) * (double)i);
        size_t tmp = cells[i];
        cells[i] = cells[j];
        cells[j] = tmp;
    }
    /* convert to a chase: cells[i] now holds the next index */
    /* we actually built a permutation; turn into a single cycle by chaining */
    /* Build cycle: visit indices in order 0 -> cells[0] -> cells[cells[0]] ... */
    /* Already a permutation, so it forms one or more cycles. To force a
       single cycle, chain through a permutation of [1..n-1] and end at 0. */
    size_t *order = (size_t *)malloc((n - 1) * sizeof(size_t));
    for (size_t i = 0; i < n - 1; i++) order[i] = i + 1;
    for (size_t i = n - 2; i > 0; i--) {
        size_t j = (size_t)((double)rand() / ((double)RAND_MAX + 1.0) * (double)(i + 1));
        size_t tmp = order[i];
        order[i] = order[j];
        order[j] = tmp;
    }
    cells[0] = order[0];
    for (size_t i = 0; i < n - 2; i++) cells[order[i]] = order[i + 1];
    cells[order[n - 2]] = 0;
    free(order);
}

static double measure(size_t bytes, size_t access_count) {
    size_t n = bytes / sizeof(size_t);
    if (n < 2) n = 2;
    size_t *cells = (size_t *)malloc(n * sizeof(size_t));
    if (!cells) return 0.0;
    build_cycle(cells, n);

    /* warm-up */
    size_t idx = 0;
    for (size_t k = 0; k < (n < access_count ? n : access_count); k++) {
        idx = cells[idx];
    }

    double t0 = now_s();
    for (size_t k = 0; k < access_count; k++) {
        idx = cells[idx];
    }
    double t1 = now_s();

    /* prevent dead-code elimination */
    if (idx == (size_t)-12345) fprintf(stderr, "x");

    free(cells);
    return (t1 - t0) * 1e9 / (double)access_count;
}

int main(int argc, char **argv) {
    size_t access_count = (argc > 1) ? strtoull(argv[1], NULL, 10) : 40000000ULL;
    static const size_t sizes[] = {
        4 * 1024,         /* 4 KB   */
        16 * 1024,        /* 16 KB  */
        64 * 1024,        /* 64 KB  */
        256 * 1024,       /* 256 KB */
        1 * 1024 * 1024,  /* 1 MB   */
        4 * 1024 * 1024,
        16 * 1024 * 1024,
        64 * 1024 * 1024,
        256 * 1024 * 1024,
        1024 * 1024 * 1024, /* 1 GB */
    };
    srand(42);
    for (size_t i = 0; i < sizeof(sizes) / sizeof(sizes[0]); i++) {
        double ns = measure(sizes[i], access_count);
        printf("{\"bytes\":%zu, \"ns_per_access\":%.4f, \"iterations\":%zu}\n",
               sizes[i], ns, access_count);
        fflush(stdout);
    }
    return 0;
}
