# Infrastructure Hardware Power Collectors Module Documentation

## Overview

The **pwr** (power) module within the `infrastructure.hardware.collectors` package represents the hardware telemetry extraction layer for power consumption metrics in the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides a robust, cross-platform mechanism for detecting and reading CPU power consumption in Watts.

This module acts as the **infrastructure implementation** for power data gathering, completely decoupled from the domain representation. It ensures that raw power readings are safely acquired across diverse environments (macOS, Linux) and fed into the benchmark's metric aggregation pipelines.

This module contains core functions for:
- **Cross-Platform CPU Power Retrieval**: Utilizing macOS `powermetrics` for Apple Silicon and Linux Intel RAPL (Running Average Power Limit) for x86/ARM Linux environments.

All collection mechanisms are designed with:
- **Graceful degradation**: Silent fallbacks and debug-level logging if a specific sensor, tool, or permission is unavailable, preventing benchmark crashes.
- **Cross-platform compatibility**: Abstracted OS-specific logic to ensure consistent behavior across Desktop and Edge environments.
- **Data validation**: Strict range checking (`0 <= power < 1000` Watts) and safe handling of hardware counter overflows (e.g., RAPL energy counter wrap-around).

---

### Folder structure

|-> `pwr/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module initialization and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `power.py` - Cross-platform CPU power detection and retrieval logic. [Learn more.](#powerpy)  

---

### [pwr](pwr) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the power collectors package.</summary><p>
>
> Initializes the package. Currently reserves the namespace for future public API exports.
>
> 🔴 `__all__`: [List[str]](#__init__py) - Currently `[]`. *Recommendation: Update to export power-related functions (e.g., `collect_cpu_power_watts`).*
>
> </p></details>

---

### [pwr](pwr) / [power.py](power.py)
> <details><summary><code>def collect_cpu_power_watts()</code> - Main entry point for CPU power retrieval.</summary><p>
>
> Dispatches to the appropriate OS-specific power collection method based on `platform.system()`.
>
> 🔴 **Returns**: [float | None](#powerpy) - The current CPU power consumption in Watts, or `None` if the platform is unsupported or the reading fails.
>
> </p></details>

> <details><summary><code>def _collect_macos_cpu_power_watts()</code> - Retrieves CPU power on macOS via powermetrics.</summary><p>
>
> Executes the `powermetrics` utility via subprocess with a short timeout to sample CPU power. Designed specifically for Apple Silicon and modern macOS environments.
>
> 🔴 **Returns**: [float | None](#powerpy) - The parsed power value in Watts, or `None` if the subprocess fails or returns an error code.
>
> </p></details>

> <details><summary><code>def _parse_macos_cpu_power(output: str)</code> - Internal helper to parse powermetrics output.</summary><p>
>
> Uses regular expressions to extract "CPU Power" or "Processor Power" values from the `powermetrics` stdout. Automatically handles unit conversion from milliwatts (mW) to Watts (W).
>
> 🔴 **Returns**: [float | None](#powerpy) - The converted power value in Watts, validated by `_is_valid_power()`.
>
> </p></details>

> <details><summary><code>def _collect_linux_rapl_cpu_power_watts()</code> - Retrieves CPU power on Linux via Intel RAPL.</summary><p>
>
> Calculates instantaneous power by reading the Intel RAPL `energy_uj` (microjoules) counter twice with a 0.1-second delay. Power is calculated as `ΔEnergy / ΔTime`. Includes safe handling for hardware counter overflow (wrap-around).
>
> 🔴 **Returns**: [float | None](#powerpy) - The calculated power in Watts, or `None` if the RAPL path is missing, unreadable, or the counter overflows.
>
> </p></details>

> <details><summary><code>def _find_rapl_energy_path()</code> - Internal helper to locate the RAPL energy counter.</summary><p>
>
> Scans `/sys/class/powercap/intel-rapl*/` to find a valid `energy_uj` file at the package level.
>
> 🔴 **Returns**: [Path | None](#powerpy) - The resolved path to the energy counter file, or `None` if not found.
>
> </p></details>

> <details><summary><code>def _is_valid_power(power_watts: float)</code> - Internal helper for data sanitization.</summary><p>
>
> Validates that a power reading is a numeric type and falls within a physically reasonable range for computing hardware, filtering out erroneous or uninitialized sensor readings.
>
> 🔴 **Returns**: [bool](#powerpy) - `True` if `0 <= power_watts < 1000`.
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, cross-platform mocks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing mocks for specific OS paths or `subprocess` calls)  
🔴 **NONE** - No tests written yet (Stubs, pending implementation, or infrastructure layer)