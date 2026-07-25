# Hardware Domain Module Documentation

## Overview

The **hardware** module represents the core domain layer for system hardware characterization within the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides a strict, immutable, and type-safe interface for representing static hardware specifications. 

This module acts as the single source of truth for hardware metadata, completely decoupled from the actual data collection logic (which resides in the `infrastructure` layer). It ensures that downstream components (reporters, analyzers, runners) interact with standardized, predictable data structures regardless of the underlying OS or hardware vendor.

This module contains 4 core hardware entities:
- **CPUInfo**: Validated representation of central processing unit specifications (architecture, cores, frequency).
- **GPUInfo**: Validated representation of graphics processing unit specifications, including VRAM and CUDA capabilities.
- **NPUInfo**: Extensible placeholder for Neural Processing Unit specifications (e.g., Rockchip RK3588, Hailo, Intel NPU).
- **TPUInfo**: Extensible placeholder for Tensor Processing Unit specifications (e.g., Google Coral).

All components are implemented as **frozen dataclasses with slots** (`@dataclass(slots=True, frozen=True)`), ensuring:
-  Strict type safety and IDE autocomplete support.
-  Memory efficiency (critical for long-running benchmark processes).
-  Immutability (prevents accidental state mutation during benchmark execution).
-  Seamless serialization to JSON/CSV via standard `dataclasses.asdict()` or custom mappers.

---

### Folder structure

|-> `hardware/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module exports and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `cpu_info.py` - CPU metadata representation. [Learn more.](#cpu_infopy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `gpu_info.py` - GPU metadata representation with CUDA awareness. [Learn more.](#gpu_infopy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `npu_info.py` - NPU metadata representation (extensible placeholder). [Learn more.](#npu_infopy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `tpu_info.py` - TPU metadata representation (extensible placeholder). [Learn more.](#tpu_infopy)

---

### [hardware](hardware) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the hardware domain.</summary><p>
>
> Exposes the core dataclasses to the rest of the application, ensuring clean import paths (e.g., `from core.domain.hardware import CPUInfo`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['CPUInfo', 'GPUInfo', 'NPUInfo', 'TPUInfo']`.
>
> </p></details>

### [hardware](hardware) / [cpu_info.py](cpu_info.py)
> <details><summary><code>class CPUInfo</code> - Represents static specifications of the Central Processing Unit.</summary><p>
>
> An immutable container for CPU metadata. Designed to be populated by infrastructure collectors (e.g., `psutil`, `lscpu`, `/proc/cpuinfo`) and passed safely through the application layer without risk of mutation.
>
> 🔴 `__init__()`: [None](#cpu_infopy) - Initializes the dataclass. Enforces strict type checking for all fields.  
> 🔴 `name`: [str | None](#cpu_infopy) - _Property_ for the full model name of the processor (e.g., "Intel(R) Core(TM) i7-10700K").  
> 🔴 `architecture`: [str | None](#cpu_infopy) - _Property_ for the CPU architecture (e.g., "x86_64", "aarch64", "ARM64").  
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
> 🔴 `name`: [str | None](#gpu_infopy) - _Property_ for the GPU model name (e.g., "NVIDIA GeForce RTX 3080", "Broadcom VideoCore"). Defaults to `None`.  
> 🔴 `memory_mb`: [int | None](#gpu_infopy) - _Property_ for the total VRAM capacity in Megabytes. Defaults to `None`.  
> 🔴 `driver_version`: [str | None](#gpu_infopy) - _Property_ for the installed GPU driver version string. Defaults to `None`.  
> 🔴 `has_cuda`: [bool](#gpu_infopy) - _Property_ indicating whether CUDA is available on this system. Defaults to `False`.  
> 🔴 `cuda_version`: [str | None](#gpu_infopy) - _Property_ for the installed CUDA toolkit version (e.g., "11.8"). Defaults to `None`.  
>
> </p></details>

### [hardware](hardware) / [npu_info.py](npu_info.py)
> <details><summary><code>class NPUInfo</code> - Extensible placeholder for Neural Processing Unit specifications.</summary><p>
>
> A reserved, immutable dataclass structure designed for future expansion. Intended to hold metadata for Edge AI accelerators such as Rockchip RK3588 NPU, Hailo-8, or Intel NPU.
>
> 🔴 `__init__()`: [None](#npu_infopy) - Currently a stub (`...`). Awaiting definition of fields like `top_sps` (Tera Operations Per Second), `driver_version`, and `supported_precisions`.  
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

> </p></details>

### [hardware](hardware) / [mps_info.py](mps_info.py)
> <details><summary><code>class TPUInfo</code> - Extensible placeholder for Tensor Processing Unit specifications.</summary><p>
>
> A reserved, immutable dataclass structure designed for future expansion. Intended to hold metadata for Google Coral Edge TPU or similar accelerators.
>
> 🔴 `__init__()`: [None](#tpu_infopy) - Currently a stub (`...`). Awaiting definition of fields like `device_path`, `driver_version`, and `max_power_watts`.  
>
> *Note: This class is exported to ensure API stability. Infrastructure collectors should return `None` for TPU data until this schema is fully defined.*

> </p></details>
---

### Testing Status Legend
🔴 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)