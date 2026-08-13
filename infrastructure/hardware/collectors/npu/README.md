# Hardware Module Documentation (Domain & Infrastructure)

## Overview

The **hardware** module represents the core layer for system hardware characterization within the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it is strictly divided into two sub-layers:

1. **Domain Layer (`core.domain.hardware`)**: Provides a strict, immutable, and type-safe interface (frozen dataclasses) for representing static hardware specifications. It is the single source of truth, completely decoupled from OS-specific APIs.
2. **Infrastructure Layer (`infrastructure.hardware.collectors`)**: Contains the concrete implementations that interact with OS APIs (e.g., `psutil`, `sysctl`, `/proc/cpuinfo`, `nvidia-smi`, `/sys/class/hailo`) to populate the domain models.

This separation ensures that downstream components (reporters, analyzers, runners) interact with standardized, predictable data structures regardless of the underlying OS or hardware vendor.

---

### Folder Structure

|-> `npu/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Exports `NPUCollector`.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `collector.py` - Main NPU orchestrator implementing `BaseHardwareCollector`.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `hailo_worker.py` - Self-contained adapter for Hailo-8/8L accelerators.  

---

## Domain Layer Reference

### [hardware](hardware) / [npu_info.py](npu_info.py)
> <details><summary><code>class NPUInfo</code> - Represents static specifications of Neural Processing Units.</summary><p>
>
> An immutable container for NPU metadata. While designed to be extensible for various Edge AI accelerators (Rockchip RK3588, Intel NPU, Google Coral), it currently holds the baseline specifications populated by the Hailo infrastructure worker.
>
> 🔴 `__init__()`: [None](#npu_infopy) - Initializes the dataclass.  
> 🔴 `name`: [str | None](#npu_infopy) - _Property_ for the NPU model name (e.g., "Hailo-8 / Hailo-8L"). Defaults to `None`.  
> 🔴 `architecture`: [str | None](#npu_infopy) - _Property_ for the host system architecture (e.g., "aarch64", "x86_64"), as NPU is typically tied to the host SoC. Defaults to `None`.  
>
> *Note: This class is intentionally minimal but extensible. Future iterations may add fields like `tops` (Tera Operations Per Second), `driver_version`, or `supported_precisions`.*
>
> </p></details>

*(Other domain classes `CPUInfo`, `GPUInfo`, `RAMInfo`, `MPSInfo`, `TPUInfo`, `PlatformType` remain as previously documented, ensuring API stability).*

---

## Infrastructure Layer: NPU Collectors

### [collectors](collectors) / [npu](npu) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for NPU collectors.</summary><p>
>
> Exposes the main orchestrator to the rest of the infrastructure layer, ensuring clean import paths (e.g., `from infrastructure.hardware.collectors.npu import NPUCollector`). Internal workers remain hidden to enforce encapsulation.
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['NPUCollector']`.
>
> </p></details>

### [collectors](collectors) / [npu](npu) / [collector.py](collector.py)
> <details><summary><code>class NPUCollector</code> - Main orchestrator implementing the BaseHardwareCollector contract.</summary><p>
>
> The central entry point for NPU data gathering. It initializes the specific hardware worker (currently `HailoWorker`) and manages the fallback logic. It is designed to be lightweight, delegating all heavy lifting to the worker.
>
> 🔴 `__init__(system_info_config)`: [None](#collectorpy) - Initializes the `HailoWorker`. The worker self-determines its availability during initialization.  
> 🔴 `get_hardware_info()`: [NPUInfo](#collectorpy) - **Contract Implementation**. Returns the pre-computed, cached `NPUInfo` dataclass from the worker.  
> 🔴 `get_metrics()`: [dict[str, MetricStatistics] | None](#collectorpy) - **Contract Implementation**. Returns a dictionary of runtime metrics (currently only `"temperature"`). Uses `time.perf_counter() * 1000.0` for monotonic, high-precision timestamping. Returns `None` if the NPU is not available.  
> 🔴 `_gather_static_info()`: [NPUInfo](#collectorpy) - Internal helper that queries the worker for static specifications during initialization.  
>
> </p></details>

### [collectors](collectors) / [npu](npu) / [hailo_worker.py](hailo_worker.py)
> <details><summary><code>class HailoWorker</code> - Self-contained adapter for Hailo-8/8L accelerators.</summary><p>
>
> Handles all Linux-specific Hailo NPU queries. It implements a robust, multi-stage fallback chain to locate temperature sensors, ensuring compatibility across different kernel configurations and carrier boards.
>
> 🔴 `is_available()`: [bool](#hailo_workerpy) - Returns `True` only if the OS is Linux and at least one Hailo-specific sysfs or hwmon path is detected.  
> 🔴 `get_info()`: [NPUInfo](#hailo_workerpy) - Returns baseline NPU metadata,