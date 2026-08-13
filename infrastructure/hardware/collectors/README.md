# Infrastructure Hardware Collectors Module Documentation

## Overview

The **hardware collectors** module represents the **Infrastructure Layer** of the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it is strictly responsible for interacting with OS-specific APIs (e.g., `psutil`, `sysctl`, `/proc/cpuinfo`, `nvidia-smi`, `sysfs`) to gather static hardware specifications and dynamic runtime telemetry. 

This module acts as the **data provider** for the Domain Layer (`core.domain.hardware` and `core.domain.system`). It ensures that downstream components (reporters, analyzers, runners) interact with standardized, predictable, and immutable data structures, completely abstracting away the underlying OS quirks, missing drivers, or hardware variations.

### Core Architectural Concepts
1. **Strict Contract Enforcement**: All collectors inherit from `BaseHardwareCollector`, guaranteeing a uniform API for the benchmark runner.
2. **Static vs. Dynamic Separation**: Static hardware info (e.g., CPU name, total RAM) is gathered *once* during initialization and cached. Dynamic metrics (e.g., utilization, temperature) are polled periodically in background threads.
3. **Graceful Degradation**: Collectors are designed to fail silently and return `None` or empty dataclasses if a specific sensor, library, or OS API is unavailable, ensuring the benchmark suite never crashes due to hardware telemetry failures.
4. **Worker/Strategy Pattern**: Complex collectors (like GPU and NPU) delegate OS-specific logic to self-contained "Worker" classes, allowing seamless fallback chains (e.g., NVML → `nvidia-smi` → MPS).

---

### Folder Structure

|-> `collectors/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module initialization and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `base.py` - Abstract base class defining the universal collector contract. [Learn more.](#basepy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `os.py` - Operating System metadata collector. [Learn more.](#ospy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `cpu/` - Cross-platform CPU data gathering (psutil, py-cpuinfo, sysfs).  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `gpu/` - GPU data gathering (NVML, SMI, MPS workers).  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `ram/` - Cross-platform RAM data gathering (psutil, device-tree heuristics).  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `npu/` - NPU data gathering (Hailo sysfs/hwmon workers).  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `tmp/` - Cross-platform thermal sensor detection and retrieval utilities.  

---

## Core Contracts & Base Implementations

### [collectors](collectors) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the hardware collectors package.</summary><p>
>
> Initializes the package. Currently reserves the namespace for future public API exports. Concrete collectors are typically imported directly from their respective sub-packages (e.g., `from infrastructure.hardware.collectors.cpu import CPUCollector`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Currently `[]`.
>
> </p></details>

### [collectors](collectors) / [base.py](base.py)
> <details><summary><code>class BaseHardwareCollector</code> - Abstract contract for all hardware collectors.</summary><p>
>
> Defines the strict interface that all concrete collectors must implement. Ensures uniform behavior, type safety, and predictable lifecycle management across the benchmark suite.
>
> 🔴 `HardwareInfoType`: [Union](#basepy) - Type alias defining the valid return types for static info (`CPUInfo`, `GPUInfo`, `NPUInfo`, `TPUInfo`, `RAMInfo`, `OSInfo`, `None`).  
> 🔴 `__init__(system_info_config)`: [None](#basepy) - Initializes the collector with optional configuration flags (e.g., enabling/disabling specific telemetry).  
> 🔴 `get_hardware_info()`: [HardwareInfoType](#basepy) - **Abstract**. Returns cached, static hardware specifications. Must be non-blocking after initial cache.  
> 🔴 `get_metrics()`: [MetricStatistics | dict | None](#basepy) - Returns a snapshot of dynamic runtime metrics. Must execute in < 50ms. Defaults to `None`.  
> 🔴 `is_available()`: [bool](#basepy) - Heuristic check to verify if the component is accessible on the current machine. Safely catches exceptions and returns `False` on failure.  
>
> </p></details>

### [collectors](collectors) / [os.py](os.py)
> <details><summary><code>class OSCollector</code> - Concrete implementation for Operating System metadata.</summary><p>
>
> A lightweight collector that implements `BaseHardwareCollector`. It uses Python's built-in `platform` module to extract static OS information. It does not require `system_info_config` as OS data is always gathered.
>
> 🔴 `__init__(system_info_config)`: [None](#ospy) - Accepts the config for interface compatibility but ignores it.  
> 🔴 `get_hardware_info()`: [OSInfo](#ospy) - **Contract Implementation**. Returns an immutable `OSInfo` dataclass populated with `system`, `release`, `kernel`, and `architecture`. Uses `empty_to_none` to ensure clean data.  
> 🔴 `get_metrics()`: [None](#ospy) - Returns `None` as the OS does not have runtime metrics in the context of the benchmark inference loop.  
>
> </p></details>

---

## Component-Specific Collectors (Summaries)

*(Note: Detailed deep-dives into the internal Worker patterns of these modules are maintained in their respective sub-package READMEs. Below is the architectural summary for the unified documentation).*

### [collectors](collectors) / [cpu/](cpu/)
> <details><summary><code>CPUCollector</code> - Cross-platform CPU data and telemetry gathering.</summary><p>
>
> Implements a robust fallback chain for CPU naming (`py-cpuinfo` → `sysctl` → `/proc/cpuinfo` → `lscpu` → `platform.processor()`). Caches static info on init. Dynamically polls `psutil.cpu_percent()` using **monotonic time** (`time.perf_counter()`) for high-precision, drift-free timestamping.
>
> 🔴 `get_hardware_info()`: [CPUInfo](#cpu) - Returns cached core counts, architecture, and max frequency.  
> 🔴 `get_metrics()`: [MetricStatistics](#cpu) - Returns a single data point of current CPU utilization (%).  
>
> </p></details>

### [collectors](collectors) / [gpu/](gpu/)
> <details><summary><code>GPUCollector</code> - Orchestrator for GPU data using the Worker Pattern.</summary><p>
>
> Delegates execution to a prioritized chain of self-contained workers: `NVMLWorker` (high-performance Python bindings) → `SMIWorker` (CLI fallback via `nvidia-smi`) → `MPSWorker` (Apple Silicon adapter). Guarantees graceful degradation across Windows, Linux, and macOS.
>
> 🔴 `get_hardware_info()`: [GPUInfo](#gpu) - Returns VRAM, CUDA version, and driver info from the first available worker.  
> 🔴 `get_metrics()`: [dict](#gpu) - Returns a dictionary of runtime metrics (`utilization`, `vram_usage`, `temperature`, `power`).  
>
> </p></details>

### [collectors](collectors) / [ram/](ram/)
> <details><summary><code>RAMCollector</code> - Cross-platform System Memory characterization.</summary><p>
>
> Uses `psutil.virtual_memory()` for total capacity. Implements a heuristic fallback chain (`_get_ram_type()`) to identify memory types, explicitly returning `"Unified Memory"` on macOS, and parsing `/proc/device-tree/model` to identify `"LPDDR"` on Edge devices (Raspberry Pi, Jetson).
>
> 🔴 `get_hardware_info()`: [RAMInfo](#ram) - Returns cached total MB and detected memory type.  
> 🔴 `get_metrics()`: [None](#ram) - Returns `None` (dynamic RAM polling is handled separately if required).  
>
> </p></details>

### [collectors](collectors) / [npu/](npu/)
> <details><summary><code>NPUCollector</code> - Orchestrator for Edge AI Accelerators (e.g., Hailo).</summary><p>
>
> Currently implements the `HailoWorker`, which scans Linux `sysfs` and `hwmon` paths to detect Hailo-8/8L accelerators and extract thermal telemetry. Designed to be easily extensible for Rockchip or Intel NPUs.
>
> 🔴 `get_hardware_info()`: [NPUInfo](#npu) - Returns cached NPU name and host architecture.  
> 🔴 `get_metrics()`: [dict](#npu) - Returns a dictionary containing the `"temperature"` metric if the sysfs node is readable.  
>
> </p></details>

---

## Thermal Telemetry Utilities

### [collectors](collectors) / [tmp/](tmp/)
> <details><summary><code>tmp</code> - Cross-platform thermal sensor detection and retrieval.</summary><p>
>
> A specialized utility module responsible for probing the system's thermal capabilities before the benchmark starts, and providing safe, validated temperature readings during execution.
>
> 🔴 `collect_temperature()`: [TemperatureCapabilitiesInfo](#tmp) - Probes CPU and GPU subsystems to build a boolean capability profile.  
> 🔴 `collect_cpu_temperature_celsius()`: [float | None](#tmp) - Executes a prioritized fallback chain: macOS (`MPSCollector`) → `psutil` → Windows WMI → Linux `sysfs` → Edge NPU sensors.  
> 🔴 `_is_valid_temperature()`: [bool](#tmp) - Internal sanitizer that filters out erroneous readings and automatically handles millikelvin-to-Celsius conversions.  
>
> </p></details>

---

### Design Principles & Best Practices Enforced

1. **Monotonic Timestamping**: All dynamic metric collection strictly uses `time.perf_counter() * 1000.0` to generate timestamps. This prevents metric timeline corruption caused by OS-level NTP clock synchronization or daylight saving time shifts.
2. **Fail-Safe Subprocess Execution**: Any interaction with external CLI tools (`nvidia-smi`, `sysctl`, `vcgencmd`) is wrapped in strict `try/except` blocks with hard timeouts (e.g., 2-5 seconds) to prevent the benchmark runner from hanging on unresponsive drivers.
3. **Zero-Overhead Static Reads**: Static hardware info is gathered exactly once during `__init__` and cached in memory. The `get_hardware_info()` method simply returns this cache, ensuring it can be called repeatedly by reporters without hitting the OS.
4. **Domain Isolation**: The infrastructure layer never leaks `psutil` objects, `subprocess` outputs, or raw dictionaries into the application layer. Everything is strictly mapped to frozen `@dataclass` domain models.

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing mocks for specific OS subprocess calls or sysfs paths)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)