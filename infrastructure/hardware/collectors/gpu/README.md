# Infrastructure Layer: GPU Collectors Documentation

## Overview

The **GPU Collectors** module resides in the infrastructure layer and is responsible for gathering static hardware information and runtime metrics from Graphics Processing Units. Engineered following the **Worker Pattern**, it ensures strict separation of concerns and robust cross-platform compatibility.

Instead of monolithic OS-checking logic, the `GPUCollector` orchestrates a chain of specialized, self-contained workers (`NVMLWorker` → `SMIWorker` → `MPSWorker`). This design guarantees **graceful degradation**: if the primary high-performance API (NVML) is unavailable, the system seamlessly falls back to CLI tools (`nvidia-smi`), and finally to platform-specific adapters (Apple MPS), preventing benchmark crashes on unsupported hardware.

---

### Folder Structure

|-> `gpu/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module exports and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `collector.py` - Main orchestrator implementing the `BaseHardwareCollector` contract. [Learn more.](#collectorpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `mps_worker.py` - Apple Metal Performance Shaders (MPS) adapter. [Learn more.](#mps_workerpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `nvml_worker.py` - NVIDIA Management Library (NVML) adapter. [Learn more.](#nvml_workerpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `smi_worker.py` - NVIDIA `nvidia-smi` CLI fallback adapter. [Learn more.](#smi_workerpy)

---

### [gpu](gpu) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the GPU collectors.</summary><p>
>
> Exposes the main orchestrator to the rest of the infrastructure layer, ensuring clean import paths (e.g., `from infrastructure.hardware.collectors.gpu import GPUCollector`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['GPUCollector']`. Internal workers remain hidden to enforce encapsulation.
>
> </p></details>

### [gpu](gpu) / [collector.py](collector.py)
> <details><summary><code>class GPUCollector</code> - Main orchestrator implementing the BaseHardwareCollector contract.</summary><p>
>
> The central entry point for GPU data gathering. It initializes all available workers and manages the fallback chain. It is designed to be lightweight, delegating all heavy lifting to the specific workers.
>
> 🔴 `__init__(system_info_config)`: [None](#collectorpy) - Initializes `NVMLWorker`, `SMIWorker`, and `MPSWorker`. Workers self-determine their availability during initialization.  
> 🔴 `get_hardware_info()`: [GPUInfo](#collectorpy) - **Contract Implementation**. Executes the fallback chain (`NVML` → `SMI` → `MPS`). Returns the first valid `GPUInfo` object, or an empty one if no GPU is detected.  
> 🔴 `_build_metric(value, unit)`: [MetricStatistics | None](#collectorpy) - Helper method that wraps raw numeric values into `MetricStatistics` objects, strictly using `time.perf_counter() * 1000.0` for monotonic, high-precision timestamping.  
> 🔴 `_detect_platform()`: [PlatformType](#collectorpy) - Heuristic platform detection. Checks for macOS first (to avoid `/proc` errors), then parses `/proc/device-tree/model` or `/etc/nv_tegra_release` for Edge devices (Jetson, Raspberry Pi, Hailo), defaulting to `DESKTOP` or `UNKNOWN`.  
>
> </p></details>

### [gpu](gpu) / [mps_worker.py](mps_worker.py)
> <details><summary><code>class MPSWorker</code> - Self-contained adapter for Apple Silicon (M1/M2/M3/M4).</summary><p>
>
> Handles all macOS-specific GPU queries. Since Apple Silicon uses Unified Memory and lacks traditional VRAM/utilization APIs, this worker gracefully returns `None` for unsupported metrics while accurately reporting static info and temperature.
>
> 🔴 `is_available()`: [bool](#mps_workerpy) - Returns `True` only if the OS is Darwin and the chip name is successfully resolved.  
> 🔴 `get_info()`: [GPUInfo](#mps_workerpy) - Retrieves the chip name via `sysctl -n machdep.cpu.brand_string` and total unified memory via `psutil.virtual_memory()`.  
> 🔴 `get_temperature()`: [float | None](#mps_workerpy) - Implements a two-stage fallback: first attempts a fast, non-blocking read via `psutil.sensors_temperatures()`. If that fails, it falls back to the heavy `powermetrics` CLI tool (with a strict 5-second timeout to prevent benchmark hangs).  
> 🔴 `get_utilization()`, `get_memory_used_mb()`, `get_power_watts()`: [float | None](#mps_workerpy) - Intentionally return `None` as macOS does not provide lightweight, user-space APIs for these specific GPU metrics.  
>
> </p></details>

### [gpu](gpu) / [nvml_worker.py](nvml_worker.py)
> <details><summary><code>class NVMLWorker</code> - Self-contained adapter for NVIDIA Management Library.</summary><p>
>
> The primary, high-performance source of truth for NVIDIA GPUs. Uses the `pynvml` Python bindings to query the NVIDIA driver directly, avoiding the overhead of subprocess calls.
>
> 🔴 `_init_nvml()`: [None](#nvml_workerpy) - Attempts to initialize `pynvml`. Silently fails and leaves handles as `None` if the library is missing or no NVIDIA GPU is present.  
> 🔴 `is_available()`: [bool](#nvml_workerpy) - Validates that both the `pynvml` module and a valid device handle were successfully acquired.  
> 🔴 `get_info()`: [GPUInfo](#nvml_workerpy) - Extracts GPU name, total VRAM, driver version, and CUDA toolkit version. Includes robust decoding for byte-string returns from the C-library.  
> 🔴 `get_utilization()`, `get_memory_used_mb()`, `get_temperature()`, `get_power_watts()`: [float | None](#nvml_workerpy) - Direct, low-latency queries to the NVIDIA driver for real-time runtime metrics.  
>
> </p></details>

### [gpu](gpu) / [smi_worker.py](smi_worker.py)
> <details><summary><code>class SMIWorker</code> - Self-contained fallback adapter for the nvidia-smi CLI.</summary><p>
>
> Acts as a resilient backup when `pynvml` is unavailable or fails to initialize, but the `nvidia-smi` command-line tool is present in the system PATH.
>
> 🔴 `__init__()`: [None](#smi_workerpy) - Uses `shutil.which("nvidia-smi")` to instantly determine if the CLI tool is available.  
> 🔴 `get_info()`: [GPUInfo](#smi_workerpy) - Queries `name,memory.total,driver_version` in a single, optimized CSV-formatted CLI call to minimize subprocess overhead.  
> 🔴 `get_float(query)`: [float | None](#smi_workerpy) - Generic method to fetch any numeric metric (e.g., `utilization.gpu`, `temperature.gpu`) by dynamically constructing the `--query-gpu` argument.  
> 🔴 `_query(query)`: [list[str] | None](#smi_workerpy) - Core execution engine. Runs the subprocess with a strict 3-second timeout, parses the first line of CSV output, and handles all `OSError` or `SubprocessError` exceptions silently to prevent benchmark crashes.  
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing mocks for specific OS subprocess calls)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)