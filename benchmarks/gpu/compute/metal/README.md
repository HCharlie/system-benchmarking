# Metal GPU compute benchmarks

This folder hosts Swift/Objective-C sources for Metal compute kernels. The
Python side only ships a capability probe today (`adapters/metal_probe.py`).
A real compute benchmark requires a small Swift program because Metal has no
useful Python binding without PyObjC plumbing.

## Suggested first kernel: SAXPY (`y = a*x + y`)

1. Create `saxpy.swift`:
   - Allocate two `MTLBuffer`s of `Float` (size N=1<<26 ≈ 256 MB).
   - Compile a Metal compute shader that does `y[i] = a*x[i] + y[i]`.
   - Run it M times with `MTLCommandBuffer.GPUStartTime/GPUEndTime` for accurate timing.
   - Print one JSON line per iteration:
     `{"kernel":"saxpy", "n":67108864, "seconds":0.0123, "gflops":12.3, "gbps":48.2}`

2. Build:
   ```bash
   swiftc -O -o .build/metal_saxpy benchmarks/gpu/compute/metal/saxpy.swift
   ```

3. Add a Python adapter `src/system_benchmarking/adapters/metal_kernel.py` that
   reads stdout JSON lines (mirror `adapters/scalar_native.py`).

4. Add a runner that wraps it like the other CPU/memory benchmarks.

## Why not Python directly?

PyObjC works but adds dependencies and pinning headaches. Compiling a tiny
Swift binary keeps the repo dependency-light and makes kernels reproducible
across machines.
