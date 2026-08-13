# Infrastructure Metrics Module Documentation

## Overview

The **metrics** module within the `infrastructure` package represents the runtime data collection and aggregation layer of the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides thread-safe, background polling mechanisms for capturing hardware telemetry (CPU, GPU) and model quality metrics during benchmark execution.

This module acts as the **infrastructure implementation** of metric collection, completely decoupled from the domain representation (which resides in `core.domain.metrics`). It ensures that raw telemetry is safely gathered, aggregated, and converted into immutable domain objects without blocking the main benchmark execution thread.

This module contains 3 core components:
- **CPUMetricsCollector**: Background thread-based collector for CPU utilization, power, and temperature metrics.
- **GPUMetricsCollector**: Background thread-based collector for GPU VRAM usage, power, utilization, and temperature metrics.
- **QualityMetricsCollector** (and **YOLOQualityMetricsCollector**): Abstract and concrete implementations for running model validation against a ground-truth dataset to compute accuracy metrics (mAP, precision, recall).

All collectors are designed with:
- **Thread-safety**: Using `threading.Lock` and `threading.Event` to safely manage background polling and state access.
- **Graceful degradation**: Automatic fallback mechanisms (e.g., disabling temperature collection after repeated failures) to prevent a single sensor failure from crashing the entire benchmark.
- **Clean separation of concerns**: Infrastructure collectors gather raw data, which is then mapped to the immutable `MetricStatistics` domain objects.

---

### Folder structure

|-> `metrics/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module initialization and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `cpu_collector.py` - Background thread collector for CPU runtime metrics. [Learn more.](#cpu_collectorpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `gpu_collector.py` - Background thread collector for GPU runtime metrics. [Learn more.](#gpu_collectorpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `quality.py` - Abstract and concrete collectors for model validation accuracy metrics. [Learn more.](#qualitypy)  

---

### [metrics](metrics) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the infrastructure metrics package.</summary><p>
>
> Initializes the package and reserves the namespace for future public API exports. Currently, components are imported directly by the benchmark runner.
>
> 🔴 `__all__`: [List[str]](#__init__py) - Currently empty `[]`. Reserved for explicit public API definition.
>
> </p></details>

---

### [metrics](metrics) / [cpu_collector.py](cpu_collector.py)
> <details><summary><code>class CPUMetricsCollector</code> - Background thread collector for CPU runtime metrics.</summary><p>
>
> Implements `BaseMetricsCollector` to continuously poll CPU utilization, power draw, and temperature at a configurable interval during a benchmark run. Designed to be thread-safe and resilient to transient sensor failures.
>
> 🔴 `__init__()`: [None](#cpu_collectorpy) - Initializes the collector with a `CPUCollector` instance and polling interval.  
> 🔴 `start()`: [None](#cpu_collectorpy) - Spawns a daemon thread to begin the background polling loop. Idempotent.  
> 🔴 `stop()`: [None](#cpu_collectorpy) - Signals the polling thread to terminate and waits for it to join.  
> 🔴 `get()`: [CPUMetrics](#cpu_collectorpy) - Returns a thread-safe copy of the aggregated `CPUMetrics` domain object.  
> 🔴 `_collect_loop()`: [None](#cpu_collectorpy) - _Internal method_ running the continuous polling loop until `_stop_event` is set.  
> 🔴 `_collect_once()`: [None](#cpu_collectorpy) - _Internal method_ fetching a single snapshot of CPU metrics and appending them to the history. Automatically disables power/temperature collection after repeated failures to prevent log spam.  
>
> **Note:** Uses `threading.Lock` to ensure that history extension and metric retrieval are atomic operations.
>
> </p></details>

---

### [metrics](metrics) / [gpu_collector.py](gpu_collector.py)
> <details><summary><code>class GPUMetricsCollector</code> - Background thread collector for GPU runtime metrics.</summary><p>
>
> Implements `BaseMetricsCollector` to continuously poll GPU VRAM usage, power draw, utilization, and temperature at a configurable interval. Mirrors the design of `CPUMetricsCollector` for consistent hardware telemetry gathering.
>
> 🔴 `__init__()`: [None](#gpu_collectorpy) - Initializes the collector with a `GPUCollector` instance and polling interval.  
> 🔴 `start()`: [None](#gpu_collectorpy) - Spawns a daemon thread to begin the background polling loop. Idempotent.  
> 🔴 `stop()`: [None](#gpu_collectorpy) - Signals the polling thread to terminate and waits for it to join.  
> 🔴 `get()`: [GPUMetrics](#gpu_collectorpy) - Returns a thread-safe copy of the aggregated `GPUMetrics` domain object.  
> 🔴 `_reset_metrics()`: [None](#gpu_collectorpy) - _Internal method_ clearing the metric history before a new benchmark run.  
> 🔴 `_collect_loop()`: [None](#gpu_collectorpy) - _Internal method_ running the continuous polling loop until `_stop_event` is set.  
> 🔴 `_collect_once()`: [None](#gpu_collectorpy) - _Internal method_ fetching a single snapshot of GPU metrics and extending the target metric histories.  
>
> **Note:** Gracefully handles `None` returns from the underlying `GPUCollector` (e.g., if no GPU is present) by simply skipping the snapshot without raising an exception.
>
> </p></details>

---

### [metrics](metrics) / [quality.py](quality.py)
> <details><summary><code>class QualityMetricsCollector</code> - Abstract base class for model validation metric collection.</summary><p>
>
> Defines the contract for collecting accuracy metrics (mAP, precision, recall) by validating a model against a ground-truth dataset.
>
> 🔴 `collect()`: [QualityMetrics](#qualitypy) - _Abstract method_ that must be implemented by subclasses to return aggregated quality metrics.  
>
> </p></details>

> <details><summary><code>class YOLOQualityMetricsCollector</code> - Concrete implementation for Ultralytics YOLO models.</summary><p>
>
> Executes the built-in YOLO validation routine (`model.val()`) on a specified dataset and extracts standard COCO evaluation metrics. Includes intelligent fallback logic for different task types (detect, segment, pose, obb).
>
> 🔴 `__init__()`: [None](#qualitypy) - Initializes with the YOLO backend, dataset path, task type, image size, and confidence threshold.  
> 🔴 `collect()`: [QualityMetrics](#qualitypy) - Runs validation (or returns cached results) and returns a `QualityMetrics` domain object.  
> 🔴 `_run_validation()`: [QualityMetrics](#qualitypy) - _Internal method_ executing `yolo_model.val()` and parsing the results.  
> 🔴 `_resolve_dataset_config()`: [Path](#qualitypy) - _Static method_ ensuring a valid `data.yaml` path is used, even if a directory is provided.  
> 🔴 `_normalize_task_type()`: [TaskType](#qualitypy) - _Static method_ converting string or enum task types to a standardized `TaskType` enum.  
> 🔴 `_select_metrics_source()`: [Any](#qualitypy) - _Internal method_ dynamically selecting the correct metric namespace (e.g., `results.seg` for segmentation, `results.box` for detection).  
> 🔴 `_safe_float()`: [float | None](#qualitypy) - _Static method_ safely converting metric values to floats, with bounds checking and warning logs for anomalies.  
>
> **Note:** Caches the results of the first `collect()` call to avoid redundant, time-consuming validation runs if the metrics are requested multiple times.
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values or thread-safety checks)  
🔴 **NONE** - No tests written yet (Stubs, pending implementation, or infrastructure layer)