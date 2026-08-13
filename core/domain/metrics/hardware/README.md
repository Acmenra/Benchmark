# Hardware Metrics Domain Module Documentation

## Overview

The **hardware** module within the `core.domain.metrics` package represents the hardware telemetry aggregation layer of the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides strict, immutable, and type-safe containers for encapsulating the statistical summaries of hardware performance collected during a benchmark run.

This module acts as the **domain representation** of hardware telemetry, completely decoupled from the actual polling mechanisms (which reside in the `infrastructure.metrics` layer). It ensures that downstream components (reporters, analyzers, and the benchmark runner) interact with standardized, predictable data structures regardless of the underlying OS, hardware vendor, or sensor availability.

This module contains 2 core metric entities:
- **CPUMetrics**: Aggregated statistical summary of Central Processing Unit telemetry (power draw, utilization, temperature).
- **GPUMetrics**: Aggregated statistical summary of Graphics Processing Unit telemetry (VRAM usage, power draw, utilization, temperature).

All components are implemented as **frozen dataclasses with slots** (`@dataclass(slots=True, frozen=True)`), ensuring:
- **Strict type safety** and IDE autocomplete support for hardware telemetry fields.
- **Memory efficiency** (critical when storing metrics for hundreds of benchmark iterations).
- **Immutability** (prevents accidental state mutation of aggregated metrics during reporting or serialization).
- **Graceful degradation** (all fields are `Optional`, allowing the system to handle environments where specific sensors are unavailable without crashing).

---

### Folder structure

|-> `hardware/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module initialization and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `cpu.py` - CPU telemetry aggregation container. [Learn more.](#cpupy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `gpu.py` - GPU telemetry aggregation container. [Learn more.](#gpupy)

---

### [hardware](hardware) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the hardware metrics domain.</summary><p>
>
> Exposes the core hardware metric dataclasses to the rest of the application, ensuring clean import paths (e.g., `from core.domain.metrics.hardware import CPUMetrics, GPUMetrics`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['CPUMetrics', 'GPUMetrics']`.
>
> </p></details>

---

### [hardware](hardware) / [cpu.py](cpu.py)
> <details><summary><code>class CPUMetrics</code> - Aggregated performance metrics for the Central Processing Unit (CPU).</summary><p>
>
> An immutable container for statistical summaries of CPU-related telemetry collected during a benchmark run. Designed to be populated by infrastructure collectors and passed safely through the application layer to reporters.
>
> 🔴 `cpu_power`: [MetricStatistics | None](#cpupy) - _Property_ representing the statistical summary of CPU power draw (in Watts). Defaults to `None`.  
> 🔴 `cpu_utilization`: [MetricStatistics | None](#cpupy) - _Property_ representing the statistical summary of CPU usage (in percent). Defaults to `None`.  
> 🔴 `cpu_temperature`: [MetricStatistics | None](#cpupy) - _Property_ representing the statistical summary of CPU thermal readings (in Celsius). Defaults to `None`.  
>
> **Note:** All fields are optional (`None`) if the respective sensor or collector is unavailable or disabled in the configuration. The `frozen=True` flag ensures the metrics cannot be accidentally mutated after aggregation.
>
> </p></details>

---

### [hardware](hardware) / [gpu.py](gpu.py)
> <details><summary><code>class GPUMetrics</code> - Aggregated performance metrics for the Graphics Processing Unit (GPU).</summary><p>
>
> An immutable container for statistical summaries of GPU-related telemetry collected during a benchmark run. Crucial for evaluating edge AI performance on devices with dedicated or integrated graphics accelerators.
>
> 🔴 `vram_usage`: [MetricStatistics | None](#gpupy) - _Property_ representing the statistical summary of Video RAM usage (in MB or percent). Defaults to `None`.  
> 🔴 `gpu_power`: [MetricStatistics | None](#gpupy) - _Property_ representing the statistical summary of GPU power draw (in Watts). Defaults to `None`.  
> 🔴 `gpu_utilization`: [MetricStatistics | None](#gpupy) - _Property_ representing the statistical summary of GPU compute usage (in percent). Defaults to `None`.  
> 🔴 `gpu_temperature`: [MetricStatistics | None](#gpupy) - _Property_ representing the statistical summary of GPU thermal readings (in Celsius). Defaults to `None`.  
>
> **Note:** All fields are optional (`None`) if the respective sensor or collector is unavailable or disabled in the configuration. The `frozen=True` flag ensures the metrics cannot be accidentally mutated after aggregation.
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values)  
🔴 **NONE** - No tests written yet (Stubs, pending implementation, or domain entities)