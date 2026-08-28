# Infrastructure Hardware Module Documentation

## Overview

The **hardware** module within the `infrastructure` package serves as the primary entry point for system introspection within the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it acts as a **Facade**, orchestrating various specialized sub-collectors to assemble a comprehensive, immutable snapshot of the host environment.

This module is strictly responsible for gathering **static hardware and OS specifications** exactly once at the start of a benchmark run. It ensures that the application layer receives a fully populated, type-safe `SystemInfo` domain aggregate, completely abstracting away the complexities of cross-platform API calls, missing drivers, or heuristic detections.

### Core Architectural Concepts
1. **Facade Pattern**: The root `HardwareCollector` provides a single, simplified interface (`get_system_info()`) to coordinate multiple underlying collectors.
2. **Zero-Overhead Execution**: All data gathering is performed during initialization. The resulting `SystemInfo` object is cached and reused, ensuring no performance penalty during the critical inference loop.
3. **Domain Isolation**: Raw system calls (e.g., `socket`, `psutil`, `sysfs`) are strictly confined to the infrastructure layer. The output is always mapped to frozen `@dataclass` domain models.
4. **Graceful Degradation**: If a specific sub-collector fails or is disabled via configuration, the orchestrator safely substitutes `None` without crashing the suite.

---

### Folder Structure

|-> `hardware/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module initialization and public API definition.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `collector.py` - Main orchestrator (Facade) for system-wide hardware introspection. [Learn more.](#collectorpy)  
|-> `collectors/` *(Specialized sub-collectors)*  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Sub-module initialization.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `base.py` - Abstract base class defining the universal collector contract.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `os.py` - Operating System metadata collector.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `cpu/` - Cross-platform CPU data gathering.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `gpu/` - GPU data gathering (NVML, SMI, MPS workers).  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `ram/` - Cross-platform RAM data gathering.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `npu/` - NPU data gathering (e.g., Hailo).  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `tmp/` - Cross-platform thermal sensor detection utilities.  

---

## Core Orchestrator

### [hardware](hardware) / [collector.py](collector.py)
> <details><summary><code>class HardwareCollector</code> - Facade for assembling the complete SystemInfo aggregate.</summary><p>
>
> The central entry point for hardware introspection. It initializes and coordinates specialized sub-collectors based on the user's `SystemInfoConfig`, assembling their outputs into a single, cohesive `SystemInfo` domain object.
>
> 🔴 `__init__(system_info_config)`: [None](#collectorpy) - Initializes the orchestrator. Instantiates `CPUCollector`, `GPUCollector`, `RAMCollector`, and `OSCollector`, passing the configuration flags to control telemetry scope.  
> 🔴 `get_system_info()`: [SystemInfo](#collectorpy) - **Main Execution Method**. Orchestrates the collection process:  
> &nbsp;&nbsp;&nbsp;&nbsp;1. Queries static info from CPU, RAM, and OS collectors.  
> &nbsp;&nbsp;&nbsp;&nbsp;2. Conditionally queries the GPU collector (if `collect_gpu` is enabled).  
> &nbsp;&nbsp;&nbsp;&nbsp;3. Conditionally probes thermal capabilities via `collect_temperature()` (if `collect_temperature` is enabled).  
> &nbsp;&nbsp;&nbsp;&nbsp;4. Resolves the host `device_name` via `socket.gethostname()`.  
> &nbsp;&nbsp;&nbsp;&nbsp;5. Infers the overall `platform` type (e.g., DESKTOP, JETSON) via the GPU collector's heuristic detector.  
> &nbsp;&nbsp;&nbsp;&nbsp;6. Returns the fully assembled, immutable `SystemInfo` dataclass.  
>
> *Architectural Note: NPU and TPU fields are currently initialized to `None` in the aggregate, reserving the schema for future edge-accelerator expansions without breaking the current API.*
>
> </p></details>

---

## Specialized Sub-Collectors

*(Note: The following section details the underlying components orchestrated by `HardwareCollector`. For deep dives into specific Worker patterns, refer to their respective sub-package READMEs).*

### [collectors](collectors) / [base.py](collectors/base.py)
> <details><summary><code>class BaseHardwareCollector</code> - Abstract contract for all hardware collectors.</summary><p>
>
> Defines the strict interface that all concrete collectors must implement. Ensures uniform behavior, type safety, and predictable lifecycle management.
>
> 🔴 `HardwareInfoType`: [Union](#basepy) - Type alias for valid static info returns (`CPUInfo`, `GPUInfo`, `RAMInfo`, `OSInfo`, `None`).  
> 🔴 `get_hardware_info()`: [HardwareInfoType](#basepy) - **Abstract**. Returns cached, static hardware specifications. Must be non-blocking after initial cache.  
> 🔴 `get_metrics()`: [MetricStatistics | dict | None](#basepy) - Returns a snapshot of dynamic runtime metrics. Defaults to `None` for static-only collectors.  
> 🔴 `is_available()`: [bool](#basepy) - Heuristic check to verify component accessibility. Safely catches exceptions.  
>
> </p></details>

### [collectors](collectors) / [os.py](collectors/os.py)
> <details><summary><code>class OSCollector</code> - Concrete implementation for Operating System metadata.</summary><p>
>
> A lightweight collector using Python's built-in `platform` module. It does not require `system_info_config` as OS data is always gathered.
>
> 🔴 `get_hardware_info()`: [OSInfo](#ospy) - Returns an immutable `OSInfo` dataclass populated with `system`, `release`, `kernel`, and `architecture`.  
>
> </p></details>

### [collectors](collectors) / [cpu/](collectors/cpu/)
> <details><summary><code>CPUCollector</code> - Cross-platform CPU data gathering.</summary><p>
>
> Implements a robust fallback chain for CPU naming (`py-cpuinfo` → `sysctl` → `/proc/cpuinfo` → `lscpu`). Caches static info on init.
>
> 🔴 `get_hardware_info()`: [CPUInfo](#cpu) - Returns cached core counts, architecture, and max frequency.  
>
> </p></details>

### [collectors](collectors) / [gpu/](collectors/gpu/)
> <details><summary><code>GPUCollector</code> - Orchestrator for GPU data using the Worker Pattern.</summary><p>
>
> Delegates execution to a prioritized chain: `NVMLWorker` → `SMIWorker` → `MPSWorker`. Guarantees graceful degradation across Windows, Linux, and macOS. Also provides the `_detect_platform()` heuristic used by the root `HardwareCollector`.
>
> 🔴 `get_hardware_info()`: [GPUInfo](#gpu) - Returns VRAM, CUDA version, and driver info from the first available worker.  
>
> </p></details>

### [collectors](collectors) / [ram/](collectors/ram/)
> <details><summary><code>RAMCollector</code> - Cross-platform System Memory characterization.</summary><p>
>
> Uses `psutil.virtual_memory()` for capacity. Implements a heuristic fallback (`_get_ram_type()`) to identify memory types (e.g., "Unified Memory" on macOS, "LPDDR" on Edge devices).
>
> 🔴 `get_hardware_info()`: [RAMInfo](#ram) - Returns cached total MB and detected memory type.  
>
> </p></details>

### [collectors](collectors) / [npu/](collectors/npu/)
> <details><summary><code>NPUCollector</code> - Orchestrator for Edge AI Accelerators.</summary><p>
>
> Currently implements the `HailoWorker`, scanning Linux `sysfs`/`hwmon` paths. Designed to be easily extensible for Rockchip or Intel NPUs.
>
> 🔴 `get_hardware_info()`: [NPUInfo](#npu) - Returns cached NPU name and host architecture.  
>
> </p></details>

---

## Thermal Telemetry Utilities

### [collectors](collectors) / [tmp/](collectors/tmp/)
> <details><summary><code>tmp</code> - Cross-platform thermal sensor detection and retrieval.</summary><p>
>
> A specialized utility module responsible for probing the system's thermal capabilities before the benchmark starts, invoked conditionally by the root `HardwareCollector`.
>
> 🔴 `collect_temperature()`: [TemperatureCapabilitiesInfo](#tmp) - Probes CPU and GPU subsystems to build a boolean capability profile.  
> 🔴 `collect_cpu_temperature_celsius()`: [float | None](#tmp) - Executes a prioritized fallback chain: macOS (`MPSCollector`) → `psutil` → Windows WMI → Linux `sysfs`.  
> 🔴 `_is_valid_temperature()`: [bool](#tmp) - Internal sanitizer that filters out erroneous readings and handles millikelvin-to-Celsius conversions.  
>
> </p></details>

---

## Design Principles & Best Practices Enforced

1. **Single Responsibility**: The root `collector.py` only *orchestrates*. It does not contain OS-specific logic; that is strictly delegated to the sub-collectors.
2. **Fail-Safe Subprocess Execution**: Any interaction with external CLI tools (`nvidia-smi`, `sysctl`, `vcgencmd`) within sub-collectors is wrapped in strict `try/except` blocks with hard timeouts (2-5 seconds) to prevent hangs.
3. **Zero-Overhead Static Reads**: Static hardware info is gathered exactly once during the `HardwareCollector` initialization phase. Subsequent calls to `get_system_info()` simply return the pre-computed aggregate.
4. **Domain Isolation**: The infrastructure layer never leaks `psutil` objects, `subprocess` outputs, or raw dictionaries into the application layer. Everything is strictly mapped to frozen `@dataclass` domain models.

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing mocks for specific OS subprocess calls or sysfs paths)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)