# Metrics Domain Module Documentation

## Overview

The **metrics** module within the `core.domain` package represents the data aggregation and statistical analysis layer of the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides strict, immutable, and type-safe containers for encapsulating performance, quality, and hardware telemetry collected during a benchmark run.

This module acts as the **domain representation** of benchmark results, completely decoupled from the actual collection mechanisms (which reside in the `infrastructure.metrics` layer). It ensures that downstream components (reporters, analyzers, and the benchmark runner) interact with standardized, predictable data structures regardless of the underlying collection strategy.

This module contains 6 core metric entities and 1 sub-module:
- **DataPoint**: Fundamental building block for time-series metric collection.
- **MetricStatistics**: Aggregated statistical summary with lazy-evaluated percentiles.
- **LatencyStats**: Specialized container for inference execution time metrics (FPS, p95, etc.).
- **QualityMetrics**: Model validation accuracy metrics (mAP, precision, recall).
- **BenchmarkResult**: High-level aggregation container for a specific test scenario.
- **ModelBenchmarkResult**: Granular aggregation container for a specific model/format combination (used for CSV/JSON reporting).
- **hardware/**: Sub-module for CPU and GPU telemetry aggregation.

All components are implemented as **frozen dataclasses with slots** (`@dataclass(slots=True, frozen=True)`), ensuring:
- **Strict type safety** and IDE autocomplete support for all telemetry fields.
- **Memory efficiency** (critical when storing metrics for hundreds of benchmark iterations).
- **Immutability** (prevents accidental state mutation of aggregated metrics during reporting or serialization).
- **Performance optimization** (lazy evaluation and caching of sorted arrays for percentile calculations).
- **Graceful degradation** (all fields are `Optional`, allowing the system to handle environments where specific sensors are unavailable without crashing).

---

### Folder structure

|-> `metrics/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module initialization and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `data_point.py` - Fundamental time-series measurement primitive. [Learn more.](#data_pointpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `statistics.py` - Statistical aggregation with lazy percentile computation. [Learn more.](#statisticspy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `latency.py` - Inference execution time and FPS metrics. [Learn more.](#latencypy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `quality.py` - Model validation accuracy metrics (mAP, precision, recall). [Learn more.](#qualitypy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `results.py` - High-level and granular benchmark result containers. [Learn more.](#resultspy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `hardware/` - CPU and GPU telemetry aggregation sub-module. [Learn more.](#hardware)

---

### [metrics](metrics) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the metrics domain.</summary><p>
>
> Exposes the core metric dataclasses and functions to the rest of the application, ensuring clean import paths (e.g., `from core.domain.metrics import ModelBenchmarkResult, LatencyStats`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['DataPoint', 'MetricStatistics', 'LatencyStats', 'CPUMetrics', 'GPUMetrics', 'QualityMetrics', 'BenchmarkResult', 'ModelBenchmarkResult']`.
>
> </p></details>

---

### [metrics](metrics) / [data_point.py](data_point.py)
> <details><summary><code>class DataPoint</code> - Represents a single, timestamped metric measurement.</summary><p>
>
> The fundamental building block for time-series metric collection, pairing a precise timestamp with a numeric value.
>
> 🔴 `time_in_ms`: [float](#data_pointpy) - _Property_ representing the absolute or relative timestamp of the measurement in milliseconds.  
> 🔴 `value`: [float | int](#data_pointpy) - _Property_ representing the numeric value of the metric (e.g., latency in ms, utilization in %).  
>
> **Note:** Immutability (`frozen=True`) is critical to ensure thread-safety when appending to shared history lists in concurrent collectors.
>
> </p></details>

---

### [metrics](metrics) / [statistics.py](statistics.py)
> <details><summary><code>class MetricStatistics</code> - Aggregated statistical summary for a series of metric measurements.</summary><p>
>
> Lazily computes and caches statistical properties (min, max, mean, percentiles) from a history of `DataPoint` objects, optimizing performance when multiple properties are accessed sequentially.
>
> 🔴 `history`: [list[DataPoint]](#statisticspy) - _Property_ representing the raw, append-only sequence of measurements.  
> 🔴 `unit`: [str | None](#statisticspy) - _Property_ representing the unit of measurement (e.g., 'ms', 'percent', 'W').  
> 🔴 `minimum`: [float | None](#statisticspy) - _Computed property_ returning the lowest recorded value.  
> 🔴 `maximum`: [float | None](#statisticspy) - _Computed property_ returning the highest recorded value.  
> 🔴 `mean`: [float | None](#statisticspy) - _Computed property_ returning the arithmetic average.  
> 🔴 `median`: [float | None](#statisticspy) - _Computed property_ returning the 50th percentile.  
> 🔴 `p95`: [float | None](#statisticspy) - _Computed property_ returning the 95th percentile.  
> 🔴 `p99`: [float | None](#statisticspy) - _Computed property_ returning the 99th percentile.  
> 🔴 `_ensure_sorted()`: [None](#statisticspy) - _Internal method_ that builds the `_sorted_values` cache on first access to ensure O(N log N) sorting happens at most once.  
>
> </p></details>

> <details><summary><code>def _percentile()</code> - Computes the value at a given percentile using the nearest-rank method.</summary><p>
>
> A helper function that assumes the input list is already sorted in ascending order to avoid redundant sorting operations during repeated calls.
>
> 🔴 `sorted_values`: [list[float]](#statisticspy) - A pre-sorted list of numeric values.  
> 🔴 `coeff`: [float](#statisticspy) - The target percentile coefficient (e.g., 0.95).  
> 🔴 **Returns**: [float](#statisticspy) - The value at the specified percentile. Returns 0.0 if the list is empty.  
>
> </p></details>

---

### [metrics](metrics) / [latency.py](latency.py)
> <details><summary><code>class LatencyStats</code> - Aggregated statistical summary of inference latency.</summary><p>
>
> Provides a comprehensive view of model execution time, including central tendency (mean, median) and tail latency (p95, p99), which are critical for real-time applications.
>
> 🔴 `fps`: [float | None](#latencypy) - _Property_ representing frames processed per second.  
> 🔴 `mean_ms`: [float | None](#latencypy) - _Property_ representing the arithmetic mean of inference time.  
> 🔴 `p50_ms`: [float | None](#latencypy) - _Property_ representing the 50th percentile (median) inference time.  
> 🔴 `p95_ms`: [float | None](#latencypy) - _Property_ representing the 95th percentile inference time.  
> 🔴 `p99_ms`: [float | None](#latencypy) - _Property_ representing the 99th percentile inference time.  
> 🔴 `min_ms`: [float | None](#latencypy) - _Property_ representing the minimum observed inference time.  
> 🔴 `max_ms`: [float | None](#latencypy) - _Property_ representing the maximum observed inference time.  
> 🔴 `from_history()`: [LatencyStats | None](#latencypy) - _Class method_ factory that constructs a `LatencyStats` instance from a list of raw `DataPoint` objects.  
>
> </p></details>

---

### [metrics](metrics) / [quality.py](quality.py)
> <details><summary><code>class QualityMetrics</code> - Aggregated model validation quality metrics.</summary><p>
>
> Captures the accuracy and reliability of the model's predictions against a ground-truth dataset, typically computed using standard object detection or segmentation evaluation protocols (e.g., COCO metrics).
>
> 🔴 `recall`: [float | None](#qualitypy) - _Property_ representing the ratio of true positive detections to all actual positives.  
> 🔴 `precision`: [float | None](#qualitypy) - _Property_ representing the ratio of true positive detections to all predicted positives.  
> 🔴 `f1_score`: [float | None](#qualitypy) - _Property_ representing the harmonic mean of precision and recall.  
> 🔴 `map50`: [float | None](#qualitypy) - _Property_ representing Mean Average Precision at IoU threshold of 0.50.  
> 🔴 `map50_95`: [float | None](#qualitypy) - _Property_ representing Mean Average Precision averaged over IoU thresholds from 0.50 to 0.95.  
>
> **Note:** Values are `None` if validation was skipped or failed. `map50_95` is the primary metric for comparing overall model detection quality.
>
> </p></details>

---

### [metrics](metrics) / [results.py](results.py)
> <details><summary><code>class BenchmarkResult</code> - Aggregated result for a single benchmark case.</summary><p>
>
> Represents the high-level outcome of a benchmark run, potentially aggregating data across multiple models or devices within a single test scenario.
>
> 🔴 `case`: [BenchmarkCase](#resultspy) - _Property_ representing the configuration scenario that was executed.  
> 🔴 `performance`: [LatencyStats | None](#resultspy) - _Property_ representing aggregated inference performance metrics.  
> 🔴 `cpu`: [CPUMetrics | None](#resultspy) - _Property_ representing aggregated CPU telemetry.  
> 🔴 `gpu`: [GPUMetrics | None](#resultspy) - _Property_ representing aggregated GPU telemetry.  
>
> </p></details>

> <details><summary><code>class ModelBenchmarkResult</code> - Detailed benchmark result for a single, specific model configuration.</summary><p>
>
> The primary data structure used for generating granular reports (e.g., CSV rows, JSON objects), mapping a specific model/format/quantization combination to its observed performance and quality metrics.
>
> 🔴 `model`: [dict[str, Any]](#resultspy) - _Property_ containing metadata (`family`, `size`, `device`, `task_type`, `format`, `quantization`).  
> 🔴 `status`: [str](#resultspy) - _Property_ representing execution outcome (`'success'`, `'failed'`, or `'skipped'`).  
> 🔴 `error`: [str | None](#resultspy) - _Property_ containing a descriptive error message if status is `'failed'` or `'skipped'`.  
> 🔴 `performance`: [LatencyStats | None](#resultspy) - _Property_ representing inference performance metrics.  
> 🔴 `cpu`: [CPUMetrics | None](#resultspy) - _Property_ representing CPU telemetry during this specific model's run.  
> 🔴 `gpu`: [GPUMetrics | None](#resultspy) - _Property_ representing GPU telemetry during this specific model's run.  
> 🔴 `quality`: [QualityMetrics | None](#resultspy) - _Property_ representing model accuracy metrics (if validation was enabled).  
>
> **Note:** Immutability ensures that once a result is yielded by the runner, it cannot be tampered with by downstream reporting pipelines.
>
> </p></details>

---

### [metrics](metrics) / [hardware/](hardware/)
> <details><summary><code>hardware/</code> - CPU and GPU telemetry aggregation sub-module.</summary><p>
>
> Contains domain representations for hardware-specific telemetry aggregation. For detailed documentation on `CPUMetrics` and `GPUMetrics`, please refer to the [Hardware Metrics Domain Module Documentation](#).
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values)  
🔴 **NONE** - No tests written yet (Stubs, pending implementation, or domain entities)