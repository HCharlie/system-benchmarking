#!/usr/bin/env bash
# Build the vendored STREAM benchmark.
#
# Output: .build/stream/stream
#
# Tunables (env vars):
#   STREAM_ARRAY_SIZE   number of doubles per array (default 100000000 = ~800MB/array)
#   STREAM_NTIMES       iterations performed by the binary itself (default 10)
#
# OpenMP support is auto-detected via Homebrew libomp. Without it, the binary
# is built single-threaded — useful for cache benchmarks but undersells DRAM
# bandwidth on multi-core machines. Install with: brew install libomp
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${REPO_ROOT}/benchmarks/memory/bandwidth/stream/stream.c"
OUT_DIR="${REPO_ROOT}/.build/stream"
OUT="${OUT_DIR}/stream"

ARRAY_SIZE="${STREAM_ARRAY_SIZE:-100000000}"
NTIMES="${STREAM_NTIMES:-10}"

mkdir -p "${OUT_DIR}"

CC="${CC:-clang}"
CFLAGS=(-O3 -DSTREAM_ARRAY_SIZE="${ARRAY_SIZE}" -DNTIMES="${NTIMES}")

OMP_PREFIX=""
if command -v brew >/dev/null 2>&1; then
  if OMP_PREFIX="$(brew --prefix libomp 2>/dev/null)" && [ -d "${OMP_PREFIX}" ]; then
    CFLAGS+=(-Xpreprocessor -fopenmp -I"${OMP_PREFIX}/include" -L"${OMP_PREFIX}/lib" -lomp)
    echo "openmp: enabled (${OMP_PREFIX})"
  else
    OMP_PREFIX=""
  fi
fi

if [ -z "${OMP_PREFIX}" ]; then
  echo "openmp: disabled (install with 'brew install libomp' for multi-threaded results)"
fi

echo "compiling: ${CC} ${CFLAGS[*]} -> ${OUT}"
"${CC}" "${CFLAGS[@]}" "${SRC}" -o "${OUT}"

echo "built ${OUT}"
echo "array size: ${ARRAY_SIZE} doubles ($((ARRAY_SIZE * 8 / 1024 / 1024)) MB per array, $((ARRAY_SIZE * 8 * 3 / 1024 / 1024)) MB total)"
echo "ntimes:     ${NTIMES}"
