# Result Format

Raw result files should be JSON. A minimal result looks like this:

```json
{
  "schema_version": "0.1",
  "timestamp": "2026-05-02T20:50:00Z",
  "device": {
    "vendor": "apple",
    "model": "MacBook Pro",
    "chip": "Apple M3 Max",
    "architecture": "arm64",
    "memory_gb": 36
  },
  "environment": {
    "os": "macOS",
    "os_version": "15.x",
    "power_mode": "automatic"
  },
  "benchmark": {
    "family": "memory",
    "name": "sequential_read_bandwidth",
    "version": "0.1"
  },
  "metrics": {
    "score": 120.5,
    "unit": "GB/s",
    "samples": [119.8, 120.7, 121.0]
  }
}
```

