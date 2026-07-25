# System Domain Module Documentation

## Overview

The **system** module represents the core domain layer for system-level aggregation within the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides a strict, immutable, and type-safe interface for representing the complete static profile of the benchmark test environment.

This module acts as the **Aggregate Root** for environment metadata. It combines disparate hardware components, operating system details, and sensor capabilities into a single, cohesive `SystemInfo` object. It is completely decoupled from the actual data collection logic (which resides in the `infrastructure` layer), ensuring that downstream components (reporters, analyzers, runners) interact with a standardized, predictable data structure regardless of the underlying platform.

This module contains 2 core entities:
- **SystemInfo**: The primary aggregate representing the complete device profile (Platform, CPU, GPU, NPU, TPU, OS, and sensor capabilities).
- **TemperatureCapabilitiesInfo**: Metadata indicating the availability of hardware temperature sensors for runtime monitoring.

All components are implemented as **frozen dataclasses with slots** (`@dataclass(slots=True, frozen=True)`), ensuring:
-  Strict type safety and IDE autocomplete support.
-  Memory efficiency (critical for long-running benchmark processes and large result sets).
-  Immutability (prevents accidental state mutation during benchmark execution or reporting).
-  Seamless serialization to JSON/CSV via standard `dataclasses.asdict()` or custom mappers.

---

### Folder structure

|-> `system/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module exports and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `system_info.py` - System aggregate and sensor capability representations. [Learn more.](#system_infopy)

---

### [system](system) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the system domain.</summary><p>
>
> Exposes the core dataclasses to the rest of the application, ensuring clean import paths (e.g., `from core.domain.system import SystemInfo`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Intended to explicitly define the public API: `['SystemInfo', 'TemperatureCapabilitiesInfo']`. 
>
> </p></details>

### [system](system) / [system_info.py](system_info.py)
> <details><summary><code>class TemperatureCapabilitiesInfo</code> - Represents the availability of hardware temperature sensors.</summary><p>
>
> An immutable container used to declare whether the underlying infrastructure is capable of reading CPU and GPU temperatures. This prevents the benchmark runner from attempting to poll sensors that do not exist or are inaccessible.
>
> 🔴 `__init__()`: [None](#system_infopy) - Initializes the dataclass. Enforces strict boolean type checking for all fields.  
> 🔴 `cpu_sensor_available`: [bool](#system_infopy) - _Property_ indicating if CPU temperature polling is supported.  
> 🔴 `gpu_sensor_available`: [bool](#system_infopy) - _Property_ indicating if GPU temperature polling is supported.  
>
> </p></details>

> <details><summary><code>class SystemInfo</code> - The Aggregate Root representing the complete static profile of the benchmark test environment.</summary><p>
>
> An immutable container that aggregates all static environmental metadata. Designed to be populated once at the start of a benchmark suite by infrastructure collectors and passed safely through the application layer to reporters and analyzers.
>
> 🔴 `__init__()`: [None](#system_infopy) - Initializes the dataclass. Enforces strict type checking for all fields, allowing `None` for optional or undetected components.  
> 🔴 `platform`: [PlatformType | None](#system_infopy) - _Property_ for the identified hardware platform type (e.g., `DESKTOP`, `JETSON`, `RASPBERRY_PI`).  
> 🔴 `device_name`: [str | None](#system_infopy) - _Property_ for the specific device hostname or model name.  
> 🔴 `cpu`: [CPUInfo | None](#system_infopy) - _Property_ containing static CPU specifications.  
> 🔴 `gpu`: [GPUInfo | None](#system_infopy) - _Property_ containing static GPU specifications.  
> 🔴 `npu`: [NPUInfo | None](#system_infopy) - _Property_ containing static NPU specifications (extensible).  
> 🔴 `tpu`: [TPUInfo | None](#system_infopy) - _Property_ containing static TPU specifications (extensible).  
> 🔴 `os`: [OSInfo | None](#system_infopy) - _Property_ containing operating system metadata.  
> 🔴 `temperature`: [TemperatureCapabilitiesInfo | None](#system_infopy) - _Property_ declaring sensor availability for runtime monitoring.  
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values)  
🔴 **NONE** - No tests written yet (Stubs, pending implementation, or untested domain entities)