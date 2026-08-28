Вот комплексная, унифицированная документация `README.md` для всего модуля `application/benchmark`. Она объединяет предоставленные вами описания подмодулей `metrics` и `reporter` с новым, детально проработанным описанием центрального компонента — `BenchmarkRunner`, сохраняя единый профессиональный стиль и структуру.

***

# Application Benchmark Module Documentation

## Overview

The **benchmark** module within the `application` layer represents the core orchestration engine of the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it coordinates the entire lifecycle of a benchmark run: from resolving model artifacts and validating hardware availability, to executing the inference loop, collecting high-precision telemetry, and delegating result persistence.

This module acts as the **central conductor**. It is completely decoupled from the low-level implementation details of hardware polling or file I/O (which reside in the `infrastructure` layer). Instead, it focuses on workflow management, state transitions, and ensuring that every benchmark case yields a standardized, immutable `ModelBenchmarkResult`, regardless of whether the execution was successful, failed, or skipped.

### Key Architectural Features
- **Lifecycle Orchestration**: Manages the strict sequence of warmup, metric collection start, inference execution, metric collection stop, and aggressive resource cleanup.
- **Dynamic Artifact Resolution**: Intelligently resolves model paths (supporting both standard Ultralytics downloads and custom local paths) and validates format/quantization compatibility before execution.
- **Graceful Degradation**: Safely skips unsupported devices (e.g., missing CUDA/MPS) or failed quantization formats, yielding a `skipped` or `failed` status result without crashing the entire benchmark suite.
- **Memory-Efficient Execution**: Utilizes Python generators (`yield`) to stream `ModelBenchmarkResult` objects as soon as a model run completes, preventing memory exhaustion during large-scale benchmark matrices.
- **Domain Alignment**: Translates raw infrastructure outputs into strict, immutable domain entities (`LatencyStats`, `CPUMetrics`, `QualityMetrics`) defined in `core.domain.metrics`.

---

### Folder Structure

|-> `benchmark/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module exports and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `runner.py` - Core orchestration engine for benchmark execution. [Learn more.](#runnerpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `metrics/` - Lifecycle management for performance and hardware data collection. [Learn more.](#metrics)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `reporter/` - Orchestration engine for output generation and persistence. [Learn more.](#reporter)  

---

## Core Components

### [benchmark](benchmark) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the application benchmark layer.</summary><p>
>
> Exposes the primary orchestrator classes to the rest of the application (e.g., the CLI entry point), ensuring clean import paths.
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['BaseReporter', 'Reporter', 'BaseMetricsCollector', 'MetricsCollector']`. *(Note: `BenchmarkRunner` is typically imported directly due to its size and specific use case).*
>
> </p></details>

---

### [benchmark](benchmark) / [runner.py](runner.py)
> <details><summary><code>class BenchmarkRunner</code> - Core orchestration engine for benchmark execution.</summary><p>
>
> The central coordinator that executes the benchmark matrix defined in the configuration. It manages dataset loading, device normalization, model artifact resolution, the inference loop, and post-run resource cleanup.
>
> 🔴 `__init__()`: [None](#runnerpy) - Initializes the runner with `BenchmarkConfig`. Instantiates base hardware collectors (CPU, GPU, RAM) and ensures the models cache directory exists.  
> 🔴 `run_suite()`: [Generator](#runnerpy) - Top-level generator that yields `ModelBenchmarkResult` objects for every case in the configuration.  
> 🔴 `_run_case()`: [Generator](#runnerpy) - Orchestrates the nested loops: devices → formats → quantizations. Handles graceful skipping of unavailable devices.  
> 🔴 `_try_resolve_model_artifact()`: [ResolvedModelArtifact | None](#runnerpy) - Complex resolution logic. Checks for custom local paths, downloads standard weights if missing, and triggers format-specific export/quantization pipelines (PyTorch, ONNX, OpenVINO, TensorRT, NCNN).  
> 🔴 `_run_model_on_data()`: [None](#runnerpy) - The core inference loop. Iterates over the dataset (real or synthetic), invoking `collector.mark_start()` and `collector.mark_stop()` around `model.predict()`.  
> 🔴 `_collect_quality_metrics()`: [QualityMetrics | None](#runnerpy) - Optionally triggers YOLO validation against a ground-truth dataset to compute mAP, precision, and recall.  
> 🔴 `_cleanup_model_resources()`: [None](#runnerpy) - **Critical for stability**. Aggressively clears predictor states, destroys OpenCV windows, and empties PyTorch CUDA/MPS caches to prevent Out-Of-Memory (OOM) errors during long runs.  
>
> *Architectural Note: Every execution path within `_run_case` is wrapped in `try...except` blocks to guarantee that a `ModelBenchmarkResult` is always yielded, even if the inference crashes, ensuring the benchmark suite never halts prematurely.*
>
> </p></details>

---

### [benchmark](benchmark) / [metrics/](metrics/)
> <details><summary><code>metrics/</code> - Orchestration engine for performance and hardware data collection.</summary><p>
>
> Acts as the bridge between the high-level benchmark runner and low-level infrastructure collectors. Focuses on lifecycle management: starting/stopping background monitors, capturing high-precision wall-clock latency, and aggregating raw data into standardized domain objects.
>
> **Key Components:**
> - 🔴 **`BaseMetricsCollector`**: The abstract contract (`start`, `stop`, `get`) that all infrastructure metric collectors must implement.  
> - 🔴 **`MetricsCollector`**: The primary orchestrator for a single benchmark case. Manages the lifecycle of CPU/GPU collectors and independently tracks per-inference latency using `time.perf_counter()` for sub-millisecond accuracy, immune to system clock drift.  
>
> *For detailed documentation, see the [Application Benchmark Metrics Module Documentation](#metrics).*
>
> </p></details>

---

### [benchmark](benchmark) / [reporter/](reporter/)
> <details><summary><code>reporter/</code> - Orchestration engine for output generation and persistence.</summary><p>
>
> Implements the **Strategy** and **Composite** design patterns. It is completely decoupled from actual file I/O or formatting logic. Instead, it focuses on iterating through enabled formats, delegating the serialization task to the appropriate infrastructure reporter, and handling unsupported format errors gracefully.
>
> **Key Components:**
> - 🔴 **`BaseReporter`**: The abstract contract defining the `report(data)` method for format-specific implementations.  
> - 🔴 **`Reporter`**: The central coordinator. Manages a registry of available reporters, normalizes format strings, and executes them sequentially. Raises explicit `ValueError` (fail-fast) if a requested format is not registered.  
>
> *For detailed documentation, see the [Application Benchmark Reporter Module Documentation](#reporter).*
>
> </p></details>

---

## Design Principles & Best Practices Enforced

1. **Generator-Based Streaming**: By using `yield` in `run_suite` and `_run_case`, the runner streams results immediately. This allows reporters to write to disk incrementally, keeping the application's memory footprint minimal regardless of the benchmark matrix size.
2. **Monotonic Timing**: All latency measurements strictly use `time.perf_counter()`, preventing metric timeline corruption caused by OS-level NTP clock synchronization or daylight saving time shifts.
3. **Fail-Safe Execution**: The inference loop and validation steps are heavily guarded by `try...except` blocks. If a model fails to load or infer, the error is captured, logged, and a `failed` result is yielded, allowing the suite to proceed to the next configuration.
4. **Aggressive Resource Management**: The `_cleanup_model_resources` method ensures that every inference backend is properly torn down. This includes nullifying predictor attributes, calling `.close()`/`.release()` methods, and explicitly invoking `torch.cuda.empty_cache()` and `gc.collect()`.
5. **Strict Domain Boundaries**: The runner never manipulates raw dictionaries or infrastructure-specific objects directly. It relies on `ResolvedModelArtifact`, `MetricsCollector`, and `QualityMetricsCollector` to return strictly typed, immutable domain entities.

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing mocks for specific hardware fallbacks or custom artifact resolution)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)