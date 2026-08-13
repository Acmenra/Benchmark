Вот единый, комплексный `README.md` для модуля `infrastructure/reporting/`. Он описывает слой персистентности (сохранения) результатов бенчмарка, сохраняя строгий архитектурный стиль и форматирование, которые мы использовали для предыдущих модулей.

***

# Infrastructure Reporting Module Documentation

## Overview

The **reporting** module represents the **Persistence and Serialization Layer** of the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it is strictly responsible for translating immutable domain objects (e.g., `ModelBenchmarkResult`, `SystemInfo`) into standardized, flat, and human-readable file formats (CSV, JSON).

This module acts as the **output boundary** of the application. It is completely decoupled from the internal structure of the domain models, relying on utility mappers (`to_report_items`, `flatten_dict`) to ensure that any new domain entity can be seamlessly persisted without modifying the reporter logic.

### Core Architectural Concepts
1. **Dynamic Schema Evolution**: The `CSVReporter` intelligently reads existing files, merges new column headers, and rewrites the dataset. This allows benchmark runs with different configurations (e.g., adding a new `gpu_temperature` metric) to be appended to the same CSV without breaking the schema.
2. **Class-Name Routing**: Reporters automatically determine the output filename based on the `__class__.__name__` of the incoming data (e.g., `ModelBenchmarkResult` → `modelbenchmarkresult_report.csv`), ensuring distinct files for distinct entities.
3. **Resilient File I/O**: Both reporters implement robust fallback mechanisms. The JSON reporter gracefully handles corrupted files by resetting the array, while the CSV reporter handles missing files and empty datasets without throwing exceptions.
4. **Data Flattening**: Nested domain objects (like `performance.fps` or `cpu.cpu_utilization.mean`) are automatically flattened into dot-notation strings, making them natively compatible with tabular formats like CSV.

---

### Folder Structure

|-> `infrastructure/reporting/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module initialization and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `csv_reporter.py` - Tabular persistence with dynamic header merging. [Learn more.](#csv_reporterpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `json_reporter.py` - Hierarchical persistence with resilient array extension. [Learn more.](#json_reporterpy)  

---

## Core Contracts & Implementations

### [reporting](reporting) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the reporting package.</summary><p>
>
> Exposes the concrete reporter implementations to the application orchestration layer (`main.py` or `Reporter` orchestrator).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['CSVReporter', 'JSONReporter']`.
>
> </p></details>

---

### [reporting](reporting) / [csv_reporter.py](csv_reporter.py)
> <details><summary><code>class CSVReporter</code> - Tabular persistence with dynamic schema evolution.</summary><p>
>
> Implements `BaseReporter` to write domain objects into flat CSV files. It utilizes `flatten_dict` to convert nested dataclasses into single-level dictionaries. Its most powerful feature is **header merging**: if a new benchmark run introduces a new metric (a new key), the reporter reads the existing CSV, unions the headers, and rewrites the file, ensuring no data is lost and columns remain aligned.
>
> 🔴 `__init__(output_dir)`: [None](#csv_reporterpy) - Initializes the reporter and ensures the target output directory exists (`os.makedirs`).  
> 🔴 `report(data)`: [None](#csv_reporterpy) - **Contract Implementation**.  
> &nbsp;&nbsp;&nbsp;&nbsp;1. Converts input to a list of items via `to_report_items`.  
> &nbsp;&nbsp;&nbsp;&nbsp;2. Derives the filename from the data's class name (e.g., `modelbenchmarkresult_report.csv`).  
> &nbsp;&nbsp;&nbsp;&nbsp;3. Flattens all items using `flatten_dict`.  
> &nbsp;&nbsp;&nbsp;&nbsp;4. Reads existing rows and headers (if the file exists).  
> &nbsp;&nbsp;&nbsp;&nbsp;5. Computes the union of all headers (existing + new).  
> &nbsp;&nbsp;&nbsp;&nbsp;6. Rewrites the CSV with the updated schema and all historical + new rows.  
>
> </p></details>

---

### [reporting](reporting) / [json_reporter.py](json_reporter.py)
> <details><summary><code>class JSONReporter</code> - Hierarchical persistence with resilient array extension.</summary><p>
>
> Implements `BaseReporter` to write domain objects into formatted JSON arrays. It preserves the nested structure of the domain models, making it ideal for programmatic consumption, API payloads, or deep-dive analytics. It includes built-in corruption recovery.
>
> 🔴 `__init__(output_dir)`: [None](#json_reporterpy) - Initializes the reporter and ensures the target output directory exists.  
> 🔴 `report(data)`: [None](#json_reporterpy) - **Contract Implementation**.  
> &nbsp;&nbsp;&nbsp;&nbsp;1. Converts input to a list of items via `to_report_items`.  
> &nbsp;&nbsp;&nbsp;&nbsp;2. Derives the filename from the data's class name (e.g., `modelbenchmarkresult_report.json`).  
> &nbsp;&nbsp;&nbsp;&nbsp;3. Attempts to read the existing JSON file. Handles both `list` and single `dict` formats.  
> &nbsp;&nbsp;&nbsp;&nbsp;4. **Resilience**: Catches `json.JSONDecodeError` and silently resets the array if the file is corrupted.  
> &nbsp;&nbsp;&nbsp;&nbsp;5. Extends the existing array with the new items.  
> &nbsp;&nbsp;&nbsp;&nbsp;6. Rewrites the JSON file with `indent=2` and `ensure_ascii=False` for readability.  
>
> </p></details>

---

### Design Principles & Best Practices Enforced

1. **Dynamic Schema Merging (CSV)**: Standard CSV writers fail or create misaligned columns when new fields are introduced in subsequent runs. By reading the existing file, computing the union of all keys, and rewriting, `CSVReporter` guarantees that the CSV remains a valid, queryable tabular dataset regardless of how the benchmark configuration evolves over time.
2. **Class-Name Routing**: By dynamically extracting `data.__class__.__name__.lower()`, the reporters eliminate the need for hardcoded filenames. If a new domain entity (e.g., `SystemInfo`) is passed to the reporter, it automatically creates `systeminfo_report.csv` without requiring code changes.
3. **Data Flattening**: CSV format strictly requires 1D data. The integration of `flatten_dict` ensures that deeply nested structures like `result.performance.p95_ms` are safely converted to `performance.p95_ms` column headers.
4. **Resilient Parsing (JSON)**: In long-running or distributed benchmark suites, JSON files can become corrupted (e.g., due to sudden power loss or process termination). The `try/except json.JSONDecodeError` block ensures the benchmark suite can recover and start a fresh array rather than crashing.
5. **Domain Isolation**: The reporters do not import or know about `ModelBenchmarkResult` or `SystemInfo`. They rely entirely on the `to_report_items` utility to handle the serialization contract, maintaining strict adherence to the Dependency Inversion Principle.

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing tests for CSV header merging or JSON corruption recovery)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)