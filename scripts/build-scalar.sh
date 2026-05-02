#!/usr/bin/env bash
# Build the native scalar CPU microbenchmark.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${REPO_ROOT}/benchmarks/cpu/scalar/native/scalar.c"
OUT_DIR="${REPO_ROOT}/.build/scalar"
OUT="${OUT_DIR}/scalar"

mkdir -p "${OUT_DIR}"

CC="${CC:-clang}"
CFLAGS=(-O3)

if [[ "$(uname -m)" == "arm64" ]]; then
  CFLAGS+=(-march=armv8.4-a+simd)
else
  CFLAGS+=(-march=native)
fi

echo "compiling: ${CC} ${CFLAGS[*]} -> ${OUT}"
"${CC}" "${CFLAGS[@]}" "${SRC}" -o "${OUT}"
echo "built ${OUT}"
