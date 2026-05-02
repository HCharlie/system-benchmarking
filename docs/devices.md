# Devices

Device files describe the machines used for benchmark runs. Store known devices
under `devices/<vendor>/` and use lowercase hyphenated filenames such as
`macbook-pro-m3-max.md` or `ryzen-9-7950x-rtx-4090.md`.

Each device entry should include:

- Vendor
- Model
- CPU or SoC
- GPU
- Memory size and configuration
- Operating system
- Driver or runtime versions when relevant
- Power mode or power limits
- Cooling and thermal notes
- Links to raw result files produced by this device
