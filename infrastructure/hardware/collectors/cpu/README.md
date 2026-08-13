# Hardware Module Documentation (Domain & Infrastructure)

## Overview

The **hardware** module represents the core layer for system hardware characterization within the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it is strictly divided into two sub-layers:

1. **Domain Layer (`core.domain.hardware`)**: Provides a strict, immutable, and type-safe interface (frozen dataclasses) for representing static hardware specifications. It is the single source of truth, completely decoupled from OS-specific APIs.
2. **Infrastructure Layer (`infrastructure.hardware.collectors`)**: Contains the concrete implementations that interact with OS APIs (e.g., `psutil`, `sysctl`, `/proc/cpuinfo`, `nvidia-smi`) to populate the domain models. 

This separation ensures that downstream components (reporters, analyzers, runners) interact with standardized, predictable data structures regardless of the underlying OS or hardware vendor.

---

### Folder Structure

|-> `cpu/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Exports `CPUCollector`.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `collector.py` - Concrete cross-platform CPU data gathering implementation.  


---

## Domain Layer Reference

*(Summary of previously defined entities)*
- **CPUInfo**: `name`, `architecture`, `physical_cores`, `logical_cores`, `max_frequency_mhz`.
- **GPUInfo**: `name`, `memory_mb`, `driver_version`, `has_cuda`, `cuda_version`.
- **RAMInfo**: `total_mb`, `type`, `speed_mhz`.
- **PlatformType**: `DESKTOP`, `JETSON`, `RASPBERRY_PI`, `INTEL_NUC`, `HAILO`, `UNKNOWN`.

---

## Infrastructure Layer: Hardware Collectors

### [collectors](collectors) / [base.py](base.py)
> <details><summary><code>class BaseHardwareCollector</code> - Abstract contract for all hardware collectors.</summary><p>
>
> Defines the strict interface that all concrete collectors (CPU, GPU, RAM, etc.) must implement. Ensures uniform behavior across the benchmark suite.
>
> 🔴 `__init__(system_info_config)`: [None](#basepy) - Initializes the collector with optional configuration flags.  
> 🔴 `get_hardware_info()`: [HardwareInfoType](#basepy) - **Abstract**. Returns cached, static hardware specifications (e.g., `CPUInfo`). Must be non-blocking after initial cache.  
> 🔴 `get_metrics()`: [MetricStatistics | dict | None](#basepy) - **Abstract**. Returns a snapshot of dynamic runtime metrics (e.g., utilization, temperature). Must execute in < 50ms.  
>
> </p></details>

### [collectors](collectors) / [cpu](cpu) / [collector.py](collector.py)
> <details><summary><code>class CPUCollector</code> - Cross-platform implementation of CPU data gathering.</summary><p>
>
> A robust, cross-platform collector that implements `BaseHardwareCollector`. It handles OS-specific quirks to reliably extract CPU metadata and runtime utilization, caching static data on initialization to ensure zero overhead during benchmarking.
>
> 🔴 `__init__(system_info_config)`: [None](#cpucollectorpy) - Calls `super()`, warms up `psutil.cpu_percent(interval=None)` for accurate first-read metrics, and caches static info via `_gather_static_info()`.  
> 🔴 `get_hardware_info()`: [CPUInfo](#cpucollectorpy) - Returns the pre-computed, cached `CPUInfo` dataclass.  
> 🔴 `get_metrics()`: [MetricStatistics](#cpucollectorpy) - Returns a single data point of current CPU utilization (%). **Critically uses `time.perf_counter() * 1000.0`** for monotonic, high-precision timestamping, avoiding OS clock sync jumps.  
> 🔴 `_gather_static_info()`: [CPUInfo](#cpucollectorpy) - Orchestrates the collection of name, architecture, cores, and frequency.  
> 🔴 `_collect_cpu_name()`: [str | None](#cpucollectorpy) - Implements a robust fallback chain for CPU naming:  
> &nbsp;&nbsp;1. `py-cpuinfo` package (most readable).  
> &nbsp;&nbsp;2. macOS: `sysctl -n machdep.cpu.brand_string`.  
> &nbsp;&nbsp;3. Linux: Parses `/proc/cpuinfo` (checks "model name", "hardware", "model"), falls back to `lscpu` command, then `platform.processor()`.  
> &nbsp;&nbsp;4. Windows: `platform.processor()`.  
> 🔴 `_collect_max_frequency_mhz()`: [float | None](#cpucollectorpy) - Uses `psutil.cpu_freq()`. Prefers `frequency.max`; if unavailable or 0, gracefully falls back to `frequency.current`.  
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values or specific OS mocking)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)