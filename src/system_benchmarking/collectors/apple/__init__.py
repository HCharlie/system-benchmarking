"""Apple platform collectors."""

from system_benchmarking.collectors.apple.device_info import (
    MANIFEST_SCHEMA_VERSION,
    collect_apple_device_info,
    collect_apple_device_manifest,
    slugify,
)

__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "collect_apple_device_info",
    "collect_apple_device_manifest",
    "slugify",
]
