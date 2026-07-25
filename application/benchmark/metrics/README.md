# Application Benchmark Metrics Module Documentation

## Overview

The **metrics** module (within the `application/benchmark` layer) represents the orchestration engine for performance and hardware data collection during benchmark execution. Engineered following Clean Architecture principles, it acts as the bridge between the high-level benchmark runner and the low-level infrastructure collectors.

This module is completely decoupled from the actual hardware polling logic (which resides in the `infrastructure` layer). Instead, it focuses on the **lifecycle management** of metric collection: starting/stopping background monitors, capturing high-precision wall-clock latency for individual inference calls, and aggregating all raw data into standardized domain `BenchmarkResult` objects.

This module contains 2 core components:
- **BaseMetricsCollector**: The abstract contract (interface) that all infrastructure metric collectors must implement.
- **MetricsCollector**: The primary orchestrator that manages the collection lifecycle for a single benchmark case, aggregating latency statistics and hardware telemetry.

Key architectural features:
-  **High-Precision Timing**: Utilizes `time.perf_counter()` for sub-millisecond accuracy in latency measurements, avoiding system clock drift.
-  **Lifecycle Management**: Clear `start_run` / `stop_run` boundaries to prevent resource leaks and ensure background threads are properly terminated.
-  **Composability**: Accepts a list of infrastructure collectors (e.g., CPU, GPU, NPU), allowing the benchmark to scale to new hardware without modifying the core orchestration logic.
-  **Domain Alignment**: Translates raw infrastructure data into strict, immutable domain entities (`LatencyStats`, `BenchmarkResult`) defined in `core.domain.metrics`.

---

### Folder structure

|-> `metrics/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module exports and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `base.py` - Abstract contract for metric collectors. [Learn more.](#basepy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `collector.py` - Primary orchestration logic for a benchmark run. [Learn more.](#collectorpy)

---

### [metrics](metrics) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the application metrics layer.</summary><p>
>
> Exposes the core collector classes to the rest of the application (primarily the `BenchmarkRunner`), ensuring clean import paths (e.g., `from application.benchmark.metrics import MetricsCollector`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['BaseMetricsCollector', 'MetricsCollector']`.
>
> </p></details>

### [metrics](metrics) / [base.py](base.py)
> <details><summary><code>class BaseMetricsCollector</code> - Abstract contract for all infrastructure metric collectors.</summary><p>
>
> Defines the standard lifecycle interface that any hardware or performance collector (CPU, GPU, NPU, etc.) must implement to be compatible with the `MetricsCollector` orchestrator.
>
> 🔴 `start()`: [None](#basepy) - _Abstract method_ to initiate background data collection (e.g., spawning a monitoring thread).  
> 🔴 `stop()`: [None](#basepy) - _Abstract method_ to halt background collection and aggregate the gathered data.  
> 🔴 `get()`: [BenchmarkResult](#basepy) - _Abstract method_ returning the aggregated metrics (e.g., `CPUMetrics` or `GPUMetrics`) for the collection period.  
>
> *Architectural Note: While the current codebase may contain stub return types (`...`), the strict contract requires `start` and `stop` to return `None`, and `get` to return a valid domain metrics object.*
>
> </p></details>

### [metrics](metrics) / [collector.py](collector.py)
> <details><summary><code>class MetricsCollector</code> - Orchestrates metric collection for a single benchmark case execution.</summary><p>
>
> The central coordinator for a benchmark run. It manages the lifecycle of multiple infrastructure collectors (CPU, GPU) and independently tracks high-precision, per-inference latency.
>
> 🔴 `__init__()`: [None](#collectorpy) - Initializes the orchestrator. Accepts the `BenchmarkCase` configuration, polling `interval_seconds`, and optional specific infrastructure collectors (defaults to CPU and GPU).  
> 🔴 `start_run()`: [None](#collectorpy) - Resets internal latency state and invokes `start()` on all registered hardware collectors.  
> 🔴 `stop_run()`: [None](#collectorpy) - Invokes `stop()` on all registered hardware collectors to finalize their data aggregation.  
> 🔴 `mark_start()`: [None](#collectorpy) - Records the high-precision start time (`time.perf_counter()`) of a single inference call.  
> 🔴 `mark_stop()`: [None](#collectorpy) - Calculates the elapsed wall-clock time in milliseconds, creates a `DataPoint`, and appends it to the internal `_latency` history. Includes safety checks for unpaired calls.  
> 🔴 `get()`: [BenchmarkResult](#collectorpy) - Aggregates the final state. Compiles `LatencyStats` from the latency history and fetches finalized hardware metrics from the infrastructure collectors, returning a complete domain `BenchmarkResult`.  
>
> *Architectural Note: This class is intentionally mutable during the run (collecting history), but produces an immutable `BenchmarkResult` upon completion.*
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values or unpaired start/stop calls)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)