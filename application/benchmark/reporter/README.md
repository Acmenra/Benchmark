# Application Benchmark Reporter Module Documentation

## Overview

The **reporter** module (within the `application/benchmark` layer) represents the orchestration engine for output generation and persistence within the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it acts as the bridge between the high-level benchmark runner and the low-level infrastructure reporters (e.g., JSON, CSV, Markdown).

This module implements the **Strategy** and **Composite** design patterns. It is completely decoupled from the actual file I/O or formatting logic (which resides in the `infrastructure` layer). Instead, it focuses on the **lifecycle management** of report generation: iterating through enabled formats, delegating the serialization task to the appropriate infrastructure reporter, and handling unsupported format errors gracefully.

This module contains 2 core components:
- **BaseReporter**: The abstract contract (interface) that all infrastructure reporters must implement.
- **Reporter**: The primary orchestrator that manages the execution of multiple reporters based on the configured output formats.

Key architectural features:
-  **Format Agnosticism**: The application layer knows nothing about JSON, CSV, or Markdown. It only knows about `BaseReporter`.
-  **Composability**: Accepts a dictionary of reporters and a list of enabled formats, allowing the benchmark to scale to new output formats without modifying the core orchestration logic.
-  **Fail-Fast Validation**: Raises explicit `ValueError` if a requested format is not registered, preventing silent failures in report generation.
-  **Domain Alignment**: Accepts raw domain entities (e.g., `BenchmarkResult`) or lists thereof, passing them down to the infrastructure layer for serialization.

---

### Folder structure

|-> `reporter/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module exports and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `base.py` - Abstract contract for infrastructure reporters. [Learn more.](#basepy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `reporter.py` - Primary orchestration logic for report generation. [Learn more.](#reporterpy)

---

### [reporter](reporter) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the application reporter layer.</summary><p>
>
> Exposes the core reporter classes to the rest of the application (primarily the `BenchmarkRunner`), ensuring clean import paths (e.g., `from application.benchmark.reporter import Reporter`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['BaseReporter', 'Reporter']`.
>
> </p></details>

### [reporter](reporter) / [base.py](base.py)
> <details><summary><code>class BaseReporter</code> - Abstract contract for all infrastructure reporters.</summary><p>
>
> Defines the standard interface that any output reporter (JSON, CSV, Markdown, etc.) must implement to be compatible with the `Reporter` orchestrator.
>
> 🔴 `report()`: [None](#basepy) - _Abstract method_ to serialize and persist the provided data (which can be a single domain entity or a list of entities). Implementations reside in the `infrastructure` layer.  
>
> *Architectural Note: This class intentionally uses `Any` for the `data` parameter to allow flexibility, though in practice it will receive domain objects like `ModelBenchmarkResult`.*
>
> </p></details>

### [reporter](reporter) / [reporter.py](reporter.py)
> <details><summary><code>class Reporter</code> - Orchestrates the execution of multiple infrastructure reporters.</summary><p>
>
> The central coordinator for output generation. It manages a registry of available reporters and executes them sequentially based on the user-defined enabled formats.
>
> 🔴 `__init__()`: [None](#reporterpy) - Initializes the orchestrator. Accepts a dictionary mapping format names (e.g., "json") to `BaseReporter` instances, and a list of `enabled_formats` to execute. Normalizes format strings to lowercase.  
> 🔴 `report()`: [None](#reporterpy) - Iterates through the `enabled_formats`. For each format, it retrieves the corresponding reporter from the registry and invokes its `report()` method. Raises a `ValueError` if a requested format is not found in the registry, ensuring fail-fast behavior for misconfigurations.  
>
> *Architectural Note: This class acts as a Composite pattern implementation, allowing the application layer to treat a single report generation call as if it were writing to multiple destinations simultaneously.*
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for unsupported formats)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)