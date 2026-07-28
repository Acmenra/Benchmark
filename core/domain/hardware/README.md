# Hardware Domain Module Documentation

## Overview

The **hardware** module represents the core domain layer for system hardware characterization within the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides a strict, immutable, and type-safe interface for representing static hardware specifications. 

This module acts as the single source of truth for hardware metadata, completely decoupled from the actual data collection logic (which resides in the `infrastructure` layer). It ensures that downstream components (reporters, analyzers, runners) interact with standardized, predictable data structures regardless of the underlying OS or hardware vendor.

This module contains 6 core hardware entities and 1 platform enumeration:
- **CPUInfo**: Validated representation of central processing unit specifications (architecture, cores, frequency).
- **GPUInfo**: Validated representation of graphics processing unit specifications, including VRAM and CUDA capabilities.
- **RAMInfo**: Implemented representation of System Memory (RAM) specifications (total capacity, type, speed).
- **MPSInfo**: Extensible placeholder for Apple Metal Performance Shader (MPS) accelerator specifications.
- **NPUInfo**: Extensible placeholder for Neural Processing Unit specifications (e.g., Rockchip RK3588, Hailo, Intel NPU).
- **TPUInfo**: Extensible placeholder for Tensor Processing Unit specifications (e.g., Google Coral).
- **PlatformType**: Enumeration defining the supported Edge AI hardware platforms (Desktop, Jetson, Raspberry Pi, etc.).

All components are implemented as **frozen dataclasses with slots** (`@dataclass(slots=True, frozen=True)`), ensuring:
- Strict type safety and IDE autocomplete support.
- Memory efficiency (critical for long-running benchmark processes).
- Immutability (prevents accidental state mutation during benchmark execution).
- Seamless serialization to JSON/CSV via standard `dataclasses.asdict()` or custom infrastructure mappers.

---

### Folder structure

|-> `hardware/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module exports and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `cpu_info.py` - CPU metadata representation. [Learn more.](#cpu_infopy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `gpu_info.py` - GPU metadata representation with CUDA awareness. [Learn more.](#gpu_infopy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `ram_info.py` - System RAM metadata representation. [Learn more.](#ram_infopy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `mps_info.py` - Apple MPS accelerator representation (extensible placeholder). [Learn more.](#mps_infopy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `npu_info.py` - NPU metadata representation (extensible placeholder). [Learn more.](#npu_infopy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `tpu_info.py` - TPU metadata representation (extensible placeholder). [Learn more.](#tpu_infopy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `enums.py` - Platform type enumeration. [Learn more.](#enumspy)

---

### [hardware](hardware) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the hardware domain.</summary><p>
>
> Exposes the core dataclasses and enumerations to the rest of the application, ensuring clean import paths (e.g., `from core.domain.hardware import CPUInfo, PlatformType`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['CPUInfo', 'GPUInfo', 'MPSInfo', 'NPUInfo', 'TPUInfo', 'RAMInfo', 'PlatformType']`.
>
> </p></details>

### [hardware](hardware) / [cpu_info.py](cpu_info.py)
> <details><summary><code>class CPUInfo</code> - Represents static specifications of the Central Processing Unit.</summary><p>
>
> An immutable container for CPU metadata. Designed to be populated by infrastructure collectors (e.g., `psutil`, `lscpu`, `/proc/cpuinfo`) and passed safely through the application layer without risk of mutation.
>
> 🔴 `__init__()`: [None](#cpu_infopy) - Initializes the dataclass. Enforces strict type checking for all fields.  
> 🔴 `name`: [str | None](#cpu_infopy) - _Property_ for the full model name of the processor (e.g., "Apple M4 Pro", "Intel(R) Core(TM) i7-10700K").  
> 🔴 `architecture`: [str | None](#cpu_infopy) - _Property_ for the CPU architecture (e.g., "x86_64", "aarch64", "arm64").  
> 🔴 `physical_cores`: [int | None](#cpu_infopy) - _Property_ for the number of physical CPU cores.  
> 🔴 `logical_cores`: [int | None](#cpu_infopy) - _Property_ for the number of logical CPU threads.  
> 🔴 `max_frequency_mhz`: [float | None](#cpu_infopy) - _Property_ for the maximum clock frequency in Megahertz.  
>
> </p></details>

### [hardware](hardware) / [gpu_info.py](gpu_info.py)
> <details><summary><code>class GPUInfo</code> - Represents static specifications and capabilities of the Graphics Processing Unit.</summary><p>
>
> An immutable container for GPU metadata. Extends basic hardware info with specific fields for driver versions and CUDA availability, which are critical for determining Edge AI inference capabilities.
>
> 🔴 `__init__()`: [None](#gpu_infopy) - Initializes the dataclass with default `None`/`False` values for optional fields.  
> 🔴 `name`: [str | None](#gpu_infopy) - _Property_ for the GPU model name (e.g., "NVIDIA GeForce RTX 3080", "Apple M4 Pro"). Defaults to `None`.  
> 🔴 `memory_mb`: [int | None](#gpu_infopy) - _Property_ for the total VRAM capacity in Megabytes (or Unified Memory for Apple Silicon). Defaults to `None`.  
> 🔴 `driver_version`: [str | None](#gpu_infopy) - _Property_ for the installed GPU driver version string. Defaults to `None`.  
> 🔴 `has_cuda`: [bool](#gpu_infopy) - _Property_ indicating whether CUDA is available on this system. Defaults to `False`.  
> 🔴 `cuda_version`: [str | None](#gpu_infopy) - _Property_ for the installed CUDA toolkit version (e.g., "11.8"). Defaults to `None`.  
>
> </p></details>

### [hardware](hardware) / [ram_info.py](ram_info.py)
> <details><summary><code>class RAMInfo</code> - Represents static specifications of System Memory (RAM).</summary><p>
>
> An immutable container for RAM metadata. Critical for Edge devices, especially those with Unified Memory architectures (like Apple Silicon or Jetson), where system RAM is dynamically shared with the GPU/NPU.
>
> 🔴 `__init__()`: [None](#ram_infopy) - Initializes the dataclass with default `None` values for optional fields.  
> 🔴 `total_mb`: [int | None](#ram_infopy) - _Property_ for the total physical memory capacity in Megabytes. Defaults to `None`.  
> 🔴 `type`: [str | None](#ram_infopy) - _Property_ for the memory type (e.g., "DDR4", "LPDDR5", "Unified Memory"). Defaults to `None`.  
> 🔴 `speed_mhz`: [float | None](#ram_infopy) - _Property_ for the memory clock frequency in Megahertz. Defaults to `None`.  
>
> </p></details>

### [hardware](hardware) / [mps_info.py](mps_info.py)
> <details><summary><code>class MPSInfo</code> - Extensible placeholder for Apple Metal Performance Shader specifications.</summary><p>
>
> A reserved, immutable dataclass structure designed for future expansion. Intended to hold detailed metadata for Apple Silicon (M1/M2/M3/M4) MPS accelerators beyond what is captured in `GPUInfo`.
>
> 🔴 `__init__()`: [None](#mps_infopy) - Currently a stub (`...`). Awaiting definition of specific fields.  
>
> *Note: This class is exported to ensure API stability. Infrastructure collectors should return `None` for MPS-specific data until this schema is fully defined.*
>
> </p></details>

### [hardware](hardware) / [npu_info.py](npu_info.py)
> <details><summary><code>class NPUInfo</code> - Extensible placeholder for Neural Processing Unit specifications.</summary><p>
>
> A reserved, immutable dataclass structure designed for future expansion. Intended to hold metadata for Edge AI accelerators such as Rockchip RK3588 NPU, Hailo-8, or Intel NPU.
>
> 🔴 `__init__()`: [None](#npu_infopy) - Currently a stub (`...`). Awaiting definition of fields like `tops` (Tera Operations Per Second), `driver_version`, and `supported_precisions`.  
>
> *Note: This class is exported to ensure API stability. Infrastructure collectors should return `None` for NPU data until this schema is fully defined.*
>
> </p></details>

### [hardware](hardware) / [tpu_info.py](tpu_info.py)
> <details><summary><code>class TPUInfo</code> - Extensible placeholder for Tensor Processing Unit specifications.</summary><p>
>
> A reserved, immutable dataclass structure designed for future expansion. Intended to hold metadata for Google Coral Edge TPU or similar accelerators.
>
> 🔴 `__init__()`: [None](#tpu_infopy) - Currently a stub (`...`). Awaiting definition of fields like `device_path`, `driver_version`, and `max_power_watts`.  
>
> *Note: This class is exported to ensure API stability. Infrastructure collectors should return `None` for TPU data until this schema is fully defined.*
>
> </p></details>

### [hardware](hardware) / [enums.py](enums.py)
> <details><summary><code>class PlatformType</code> - Enumeration of supported Edge AI hardware platforms.</summary><p>
>
> Defines the standard hardware targets for the benchmark suite. Used by the `SystemInfo` aggregate to classify the test environment.
>
> 🔴 `DESKTOP`: [str](#enumspy) - Standard x86_64 PC, Server, or Apple Silicon Mac.  
> 🔴 `JETSON`: [str](#enumspy) - NVIDIA Jetson family (Nano, Xavier, Orin).  
> 🔴 `RASPBERRY_PI`: [str](#enumspy) - Raspberry Pi family (Compute Modules and SBCs).  
> 🔴 `INTEL_NUC`: [str](#enumspy) - Intel NUC or similar compact x86 Edge PCs.  
> 🔴 `HAILO`: [str](#enumspy) - Systems equipped with Hailo AI accelerators.  
> 🔴 `UNKNOWN`: [str](#enumspy) - Fallback for unrecognized or unsupported platforms.  
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)