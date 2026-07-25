# Operating System Domain Module Documentation

## Overview

The **operating_system** module represents the core domain layer for system environment characterization within the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides a strict, immutable, and type-safe interface for representing static operating system specifications. 

This module acts as the single source of truth for OS metadata, completely decoupled from the actual data collection logic (which resides in the `infrastructure` layer, typically using Python's built-in `platform` module). It ensures that downstream components (reporters, analyzers, runners) interact with standardized, predictable data structures regardless of the underlying platform (Linux, Windows, macOS, Jetson, Raspberry Pi).

This module contains 1 core entity:
- **OSInfo**: Validated representation of operating system metadata (name, release, kernel, architecture).

All components are implemented as **frozen dataclasses with slots** (`@dataclass(slots=True, frozen=True)`), ensuring:
-  Strict type safety and IDE autocomplete support.
-  Memory efficiency (critical for long-running benchmark processes).
-  Immutability (prevents accidental state mutation during benchmark execution).
-  Seamless serialization to JSON/CSV via standard `dataclasses.asdict()` or custom mappers.

---

### Folder structure

|-> `operating_system/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module exports and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `operating_system.py` - OS metadata representation. [Learn more.](#operating_systempy)

---

### [operating_system](operating_system) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the operating system domain.</summary><p>
>
> Exposes the core dataclasses to the rest of the application, ensuring clean import paths (e.g., `from core.domain.operating_system import OSInfo`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Intended to explicitly define the public API (e.g., `['OSInfo']`). *Note: Currently empty in the provided snippet; requires update to `['OSInfo']` for proper public API exposure and linter compliance.*
>
> </p></details>

### [operating_system](operating_system) / [operating_system.py](operating_system.py)
> <details><summary><code>class OSInfo</code> - Represents static specifications of the host Operating System.</summary><p>
>
> An immutable container for OS metadata. Designed to be populated by infrastructure collectors and passed safely through the application layer without risk of mutation.
>
> 🔴 `__init__()`: [None](#operating_systempy) - Initializes the dataclass. Enforces strict type checking for all fields.  
> 🔴 `system`: [str | None](#operating_systempy) - _Property_ for the OS name (e.g., "Linux", "Windows", "Darwin").  
> 🔴 `release`: [str | None](#operating_systempy) - _Property_ for the OS release version (e.g., "20.04", "11", "14.2").  
> 🔴 `kernel`: [str | None](#operating_systempy) - _Property_ for the OS kernel version (e.g., "5.15.0-76-generic").  
> 🔴 `architecture`: [str | None](#operating_systempy) - _Property_ for the system architecture (e.g., "x86_64", "aarch64", "ARM64").  
>
> </p></details>

---

### Testing Status Legend
🔴 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🔴 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)