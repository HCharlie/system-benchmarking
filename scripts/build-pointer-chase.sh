#!/usr/bin/env bash
# Build the pointer-chase memory latency benchmark.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${REPO_ROOT}/benchmarks/memory/latency/native/pointer_chase.c"
OUT_DIR="${REPO_ROOT}/.build/pointer_chase"
OUT="${OUT_DIR}/pointer_chase"

mkdir -p "${OUT_DIR}"

CC="${CC:-clang}"
CFLAGS=(-O3)
if [[ "$(uname -m)" == "arm64" ]]; then
  CFLAGS+=(-march=armv8.4-a)
else
  CFLAGS+=(-march=native)
fi

echo "compiling: ${CC} ${CFLAGS[*]} -> ${OUT}"
"${CC}" "${CFLAGS[@]}" "${SRC}" -o "${OUT}"
echo "built ${OUT}"
