Вот комплексная и структурированная документация `README.md` для модуля `infrastructure/utils/`, выполненная в строгом архитектурном стиле, который мы использовали для всех предыдущих модулей.

***

# Infrastructure Utilities Module Documentation

## Overview

The **utils** module within the `infrastructure` package serves as the **Data Transformation and Safe I/O Layer** of the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides a collection of stateless, pure functions designed to bridge the gap between strictly typed domain objects and flexible serialization or OS-level operations.

This module is completely decoupled from business logic. Its sole responsibility is to ensure that complex, nested domain entities (like `ModelBenchmarkResult` or `MetricStatistics`) can be safely flattened, serialized to JSON/CSV, and that hardware telemetry can be read from the OS without risking application crashes due to missing files or malformed strings.

### Core Architectural Concepts
1. **Statelessness & Thread-Safety**: All functions are pure and do not maintain internal state, making them perfectly safe for concurrent execution in multi-threaded benchmark reporters.
2. **Resilient I/O**: File reading functions (`read_text`, `read_int`) are wrapped in strict `try/except` blocks. They return safe defaults (`""` or `None`) instead of raising `OSError`, which is critical when reading volatile `sysfs` or `procfs` nodes.
3. **Recursive Serialization**: The `to_plain_data` function recursively traverses arbitrarily deep dataclasses, Enums, and dictionaries, ensuring no data is lost during report generation.
4. **Tabular Compatibility**: The `flatten_dict` utility explicitly converts nested lists into JSON strings, preventing CSV writers from breaking when encountering array-type fields.

---

### Folder Structure

|-> `utils/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module initialization.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `utils.py` - Core data transformation, serialization, and safe I/O utilities. [Learn more.](#utilspy)  

---

## Core Utilities

### [utils](utils) / [utils.py](utils.py)

> <details><summary><code>def to_plain_data()</code> - Recursive converter for domain objects to serializable primitives.</summary><p>
> Transforms complex, nested domain objects into standard Python primitives (`dict`, `list`, `str`, `int`, `float`) suitable for JSON/CSV serialization.
> 
> 🔴 `value`: [Any](#utilspy) - The input object to convert (e.g., `Path`, `Enum`, `MetricStatistics`, `dataclass`).  
> 🔴 **Returns**: [Any](#utilspy) - A primitive representation.  
> 
> **Note:** This function is the foundation of the reporting pipeline, ensuring that infrastructure reporters never have to handle custom domain types directly.
> </p></details>

> <details><summary><code>def flatten_dict()</code> - Flattens nested dictionaries into dot-notation keys.</summary><p>
> Converts deeply nested dictionaries into a single-level dictionary using dot-notation for keys (e.g., `cpu.utilization.mean`). Lists are serialized into JSON strings to maintain tabular compatibility.
> 
> 🔴 `data`: [Dict[str, Any]](#utilspy) - The nested dictionary to flatten.  
> 🔴 `prefix`: [str](#utilspy) - Internal prefix for recursive calls.  
> 🔴 **Returns**: [Dict[str, Any]](#utilspy) - A flat dictionary.  
> 
> **Note:** Essential for the `CSVReporter`, which requires strictly 1D data structures.
> </p></details>

> <details><summary><code>def to_report_items()</code> - Normalizes input data for reporters.</summary><p>
> Ensures that the input to reporters is always a list of dictionaries, regardless of whether a single entity or a list of entities was passed.
> 
> 🔴 `data`: [Any](#utilspy) - A single domain object, a list of objects, or primitives.  
> 🔴 **Returns**: [List[Dict[str, Any]]](#utilspy) - A normalized list of dictionaries ready for flattening and serialization.  
> </p></details>

> <details><summary><code>def _metric_statistics_to_report()</code> - Aggregates MetricStatistics into a summary dictionary.</summary><p>
> Extracts the core statistical properties from a `MetricStatistics` object, filtering out startup zeros to ensure accurate reporting.
> 
> 🔴 `metric`: [MetricStatistics](#utilspy) - The metric container.  
> 🔴 **Returns**: [dict[str, Any]](#utilspy) - A compact dictionary containing `unit`, `samples`, `mean`, `p50`, `p95`, `p99`, `min`, and `max`.  
> </p></details>

> <details><summary><code>def _metric_values_without_startup_zero()</code> - Filters startup zeros from metric history.</summary><p>
> Removes leading `0.0` values from the metric history, which often occur due to collector initialization delays, ensuring statistical aggregates accurately reflect the actual benchmark workload.
> 
> 🔴 `metric`: [MetricStatistics](#utilspy) - The metric container.  
> 🔴 **Returns**: [list[float | int]](#utilspy) - A cleaned list of numeric values.  
> </p></details>

> <details><summary><code>def _mean()</code> & <code>def _percentile()</code> - Statistical calculation helpers.</summary><p>
> Pure functions for calculating the arithmetic mean and nearest-rank percentiles from a list of numeric values.
> 
> 🔴 **Returns**: [float | None](#utilspy) - The calculated value, or `None` if the input list is empty.  
> </p></details>

> <details><summary><code>def read_text()</code> & <code>def read_int()</code> - Safe file reading utilities.</summary><p>
> Reads text or integer values from a file path, typically used for parsing Linux `sysfs` or `procfs` hardware telemetry nodes (e.g., `/sys/class/thermal/...`).
> 
> 🔴 `path`: [Path](#utilspy) - The file path to read.  
> 🔴 **Returns**: [str](#utilspy) or [int | None](#utilspy) - The parsed content, or `""` / `None` if the file is missing, unreadable, or contains invalid data. Catches `OSError` and `ValueError` silently.  
> </p></details>

> <details><summary><code>def to_float()</code> & <code>def to_int()</code> - Safe string parsing utilities.</summary><p>
> Converts string representations of numbers to `float` or `int`, safely handling malformed strings (e.g., from CLI tool outputs).
> 
> 🔴 `value`: [str](#utilspy) - The string to parse.  
> 🔴 **Returns**: [float | None](#utilspy) or [int | None](#utilspy) - The parsed number, or `None` if conversion fails.  
> </p></details>

> <details><summary><code>def empty_to_none()</code> - String sanitization utility.</summary><p>
> Strips whitespace from a string and returns `None` if the result is empty. Used to clean up hardware metadata (e.g., CPU names) before populating domain dataclasses.
> 
> 🔴 `value`: [str](#utilspy) - The raw string.  
> 🔴 **Returns**: [str | None](#utilspy) - The stripped string, or `None`.  
> </p></details>

---

## Design Principles & Best Practices Enforced

1. **Pure Functions & Statelessness**: All utility functions are stateless and do not modify their inputs. This guarantees thread-safety when multiple reporters or collectors process data concurrently.
2. **Fail-Safe I/O**: Functions like `read_int` and `read_text` are designed for the unpredictable nature of OS-level hardware sensors. They never raise exceptions on missing files or permission errors, ensuring the benchmark suite continues running even if a specific sensor node disappears.
3. **Recursive Serialization**: `to_plain_data` uses recursion to handle arbitrarily deep domain models. This means new fields added to `ModelBenchmarkResult` or `SystemInfo` will automatically be included in reports without requiring changes to the serialization logic.
4. **Tabular Compatibility**: `flatten_dict` explicitly converts lists to JSON strings. This prevents CSV writers from breaking when encountering array fields, ensuring the output remains a valid, parseable tabular format.
5. **Startup Noise Filtering**: `_metric_values_without_startup_zero` intelligently removes initialization artifacts from telemetry data, ensuring that statistical aggregates (like mean CPU utilization) accurately reflect the actual benchmark workload.

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, edge cases for empty lists, malformed strings, deeply nested dataclasses)  
🟡 **PARTIAL** - Basic happy-path tests exist, but edge cases (e.g., deeply nested cycles, specific OS permission errors) need more coverage  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)