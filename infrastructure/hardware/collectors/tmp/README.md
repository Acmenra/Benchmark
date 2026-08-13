# Infrastructure Hardware Temperature Collectors Module Documentation

## Overview

The **tmp** (temperature) module within the `infrastructure.hardware.collectors` package represents the hardware telemetry extraction layer for thermal sensors in the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides a robust, cross-platform mechanism for detecting and reading CPU, GPU, and SoC temperatures.

This module acts as the **infrastructure implementation** for thermal data gathering, completely decoupled from the domain representation (which resides in `core.domain.system`). It ensures that raw temperature readings are safely acquired across diverse environments (Windows, macOS, Linux, Raspberry Pi, NVIDIA Jetson) and mapped to the `TemperatureCapabilitiesInfo` domain object.

This module contains core functions for:
- **Temperature Capability Detection**: Probing the system to determine if CPU and GPU thermal sensors are accessible before the benchmark starts.
- **Cross-Platform CPU Temperature Retrieval**: Utilizing `psutil`, Windows WMI, Linux sysfs (`/sys/class/thermal`), and platform-specific fallbacks (e.g., NPU collectors on edge devices).
- **Cross-Platform GPU Temperature Retrieval**: Leveraging `pynvml`, `nvidia-smi`, `vcgencmd` (Raspberry Pi), and Tegra thermal zones (NVIDIA Jetson).

All collection mechanisms are designed with:
- **Graceful degradation**: Silent fallbacks and debug-level logging if a specific sensor or tool is unavailable, preventing benchmark crashes.
- **Cross-platform compatibility**: Abstracted OS-specific logic to ensure consistent behavior across Desktop, Edge, and Mobile environments.
- **Data validation**: Strict range checking (`0°C <= temp < 150°C`) to filter out erroneous, uninitialized, or millikelvin-scaled sensor readings.

---

### Folder structure

|-> `tmp/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module initialization and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `collector.py` - Cross-platform temperature detection and retrieval logic. [Learn more.](#collectorpy)  

*(Note: The `__init__.py` currently exports `RAMCollector`, which appears to be a legacy copy-paste artifact. It is recommended to update this to export temperature-related symbols or leave it empty if the module is accessed directly via `collector.py`).*

---

### [tmp](tmp) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the temperature collectors package.</summary><p>
>
> Initializes the package. Currently contains a legacy import (`RAMCollector`). 
>
> 🔴 `__all__`: [List[str]](#__init__py) - Currently `['RAMCollector']`. *Recommendation: Update to export temperature-related functions or classes (e.g., `collect_temperature`).*
>
> </p></details>

---

### [tmp](tmp) / [collector.py](collector.py)
> <details><summary><code>def collect_temperature()</code> - Determines the availability of thermal sensors on the current system.</summary><p>
>
> Probes both CPU and GPU subsystems to build a capability profile before the benchmark run begins.
>
> 🔴 **Returns**: [TemperatureCapabilitiesInfo](#collectorpy) - A domain object containing boolean flags `cpu_sensor_available` and `gpu_sensor_available`.
>
> </p></details>

> <details><summary><code>def collect_cpu_temperature_celsius()</code> - Retrieves the current CPU/SoC temperature in degrees Celsius.</summary><p>
>
> Executes a prioritized, cross-platform fallback chain to find a valid temperature reading:
> 1. **macOS**: Attempts to read via `MPSCollector` (Apple Silicon SoC/MPS temperature).
> 2. **System APIs**: Falls back to `psutil.sensors_temperatures()` or Windows WMI.
> 3. **Linux sysfs**: Scans `/sys/class/thermal/` and `/sys/class/hwmon/` for valid thermal zones.
> 4. **Edge Devices**: Attempts to read via `NPUCollector` on Linux edge platforms.
>
> 🔴 **Returns**: [float | None](#collectorpy) - The temperature in Celsius, or `None` if no valid sensor is found.
>
> </p></details>

> <details><summary><code>def _check_cpu_temperature_available()</code> - Internal helper to verify CPU sensor accessibility.</summary><p>
>
> 🔴 **Returns**: [bool](#collectorpy) - `True` if `collect_cpu_temperature_celsius()` returns a valid float.
>
> </p></details>

> <details><summary><code>def _check_gpu_temperature_available()</code> - Internal helper to verify GPU sensor accessibility.</summary><p>
>
> Probes GPU sensors via a prioritized fallback chain:
> 1. **NVIDIA (Python)**: `pynvml` library initialization and read.
> 2. **NVIDIA (CLI)**: `nvidia-smi` subprocess fallback.
> 3. **Platform-specific**: Raspberry Pi (`vcgencmd`) or NVIDIA Jetson (Tegra thermal zones).
>
> 🔴 **Returns**: [bool](#collectorpy) - `True` if any GPU temperature source is successfully validated.
>
> </p></details>

> <details><summary><code>def _is_valid_temperature()</code> - Internal helper for data sanitization.</summary><p>
>
> Validates that a temperature reading is a numeric type and falls within a physically reasonable range for computing hardware, automatically handling millikelvin-to-Celsius conversions if the raw value is `>= 1000`.
>
> 🔴 **Returns**: [bool](#collectorpy) - `True` if `0 <= temp < 150`.
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, cross-platform mocks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing mocks for specific OS paths or `subprocess` calls)  
🔴 **NONE** - No tests written yet (Stubs, pending implementation, or infrastructure layer)