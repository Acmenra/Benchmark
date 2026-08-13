# Hardware Module Documentation (Domain & Infrastructure)

## Overview

The **hardware** module represents the core layer for system hardware characterization within the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it is strictly divided into two sub-layers:

1. **Domain Layer (`core.domain.hardware`)**: Provides a strict, immutable, and type-safe interface (frozen dataclasses) for representing static hardware specifications. It is the single source of truth, completely decoupled from OS-specific APIs.
2. **Infrastructure Layer (`infrastructure.hardware.collectors`)**: Contains the concrete implementations that interact with OS APIs (e.g., `psutil`, `sysctl`, `/proc/cpuinfo`, `/proc/device-tree/model`) to populate the domain models.

This separation ensures that downstream components (reporters, analyzers, runners) interact with standardized, predictable data structures regardless of the underlying OS or hardware vendor.

---

### Folder Structure

|-> `ram/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Exports `RAMCollector`.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `collector.py` - Cross-platform RAM data gathering implementation.  

---

## Domain Layer Reference

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

*(Other domain classes `CPUInfo`, `GPUInfo`, `NPUInfo`, `MPSInfo`, `TPUInfo`, `PlatformType` remain as previously documented, ensuring API stability).*

---

## Infrastructure Layer: RAM Collectors

### [collectors](collectors) / [ram](ram) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for RAM collectors.</summary><p>
>
> Exposes the main orchestrator to the rest of the infrastructure layer, ensuring clean import paths (e.g., `from infrastructure.hardware.collectors.ram import RAMCollector`). Internal implementation details remain hidden to enforce encapsulation.
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['RAMCollector']`.
>
> </p></details>

### [collectors](collectors) / [ram](ram) / [collector.py](collector.py)
> <details><summary><code>class RAMCollector</code> - Cross-platform implementation of RAM data gathering.</summary><p>
>
> A robust, cross-platform collector that implements `BaseHardwareCollector`. It handles OS-specific quirks to reliably extract RAM metadata (total capacity and type), caching static data on initialization to ensure zero overhead during benchmarking.
>
> 🔴 `__init__(system_info_config)`: [None](#collectorpy) - Initializes the collector and pre-computes static info via `_gather_static_info()`.  
> 🔴 `get_hardware_info()`: [RAMInfo](#collectorpy) - **Contract Implementation**. Returns the pre-computed, cached `RAMInfo` dataclass.  
> 🔴 `get_metrics()`: [None](#collectorpy) - **Contract Implementation**. Returns `None` as this collector is strictly responsible for static hardware characterization in the current benchmark context. Dynamic usage metrics are handled separately if needed.  
> 🔴 `_gather_static_info()`: [RAMInfo](#collectorpy) - Orchestrates the collection of total memory (via `psutil.virtual_memory()`, converted to Megabytes) and delegates type detection to `_get_ram_type()`.  
> 🔴 `_get_ram_type()`: [str | None](#collectorpy) - Implements a heuristic fallback chain for RAM typing:  
> &nbsp;&nbsp;1. macOS (`Darwin`): Explicitly returns `"Unified Memory"`.  
> &nbsp;&nbsp;2. Linux: Reads `/proc/device-tree/model` via subprocess to detect Edge devices (e.g., Raspberry Pi, Jetson/Orin) and returns `"LPDDR"`. Gracefully falls back to `None` for standard desktop Linux where generic DDR type detection requires privileged access.  
>
> </p></details>

---

### Design Principles & Best Practices Enforced

1. **Worker Pattern & Encapsulation**: Each hardware component (CPU, GPU, RAM, NPU) uses self-contained logic. The `RAMCollector` cleanly separates total capacity gathering (`psutil`) from heuristic type detection (`_get_ram_type`).
2. **Graceful Degradation**: The RAM collector silently returns `None` for `type` or `total_mb` if `psutil` is missing or OS detection fails, preventing the entire benchmark suite from crashing on minimal or restricted environments.
3. **Fail-Safe Subprocess Execution**: The `_get_ram_type` method wraps the `/proc/device-tree/model` read in a `try/except` block with a strict 2-second timeout, ensuring that missing device tree files do not halt the benchmarking process.
4. **Zero-Overhead Static Reads**: Static hardware info is gathered exactly once during `__init__` and cached. The `get_hardware_info()` method simply returns this cache, ensuring it can be called repeatedly by reporters without hitting the OS.

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing mocks for specific OS subprocess calls or sysfs paths)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)