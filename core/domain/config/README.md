# Configuration Domain Module Documentation

## Overview

The **config** module represents the core domain layer for application settings and benchmark orchestration parameters within the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides a strict, immutable, and type-safe interface for defining how benchmark scenarios are structured, executed, and reported.

This module acts as the single source of truth for benchmark configuration metadata, completely decoupled from the actual YAML parsing logic (which resides in the `infrastructure` layer). It ensures that downstream components (runners, collectors, reporters) interact with standardized, predictable data structures regardless of the underlying configuration file format.

This module contains 6 core configuration entities:
- **BaseConfig**: Abstract marker interface for all configuration entities, ensuring type consistency across the domain.
- **ModelConfig**: Validated representation of a single model's parameters (family, size).
- **BenchmarkCase**: Definition of a single benchmark scenario (formerly `BenchmarkRun`), grouping models to be tested together.
- **BenchmarkConfig**: Global benchmark parameters (formats, quantization, iterations, device settings).
- **SystemInfoConfig**: Toggles for hardware telemetry collection (GPU, power, temperature).
- **ReportConfig**: Settings for output generation (directory, formats, timestamps).
- **Config**: The root aggregate combining all configuration sections into a single application state.

All components are implemented as **frozen dataclasses with slots** (`@dataclass(slots=True, frozen=True)`), ensuring:
-  Strict type safety and IDE autocomplete support.
-  Memory efficiency (critical when passing configurations across multiple workers).
-  Immutability (prevents accidental state mutation during benchmark execution).
-  Seamless serialization to JSON/CSV via standard `dataclasses.asdict()` or custom infrastructure mappers.

---

### Folder structure

|-> `config/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module exports and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `base.py` - Abstract marker interface for configuration entities. [Learn more.](#basepy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `model.py` - Model-specific configuration parameters. [Learn more.](#modelpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `benchmark.py` - Scenario and global benchmark settings. [Learn more.](#benchmarkpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `system.py` - Hardware telemetry collection toggles. [Learn more.](#systempy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `report.py` - Output and reporting settings. [Learn more.](#reportpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `root.py` - Root configuration aggregate. [Learn more.](#rootpy)

---

### [config](config) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the configuration domain.</summary><p>
>
> Exposes the core dataclasses to the rest of the application, ensuring clean import paths (e.g., `from core.domain.config import Config, BenchmarkCase`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['Config', 'SystemInfoConfig', 'BaseConfig', 'BenchmarkCase', 'BenchmarkConfig', 'ModelConfig', 'ReportConfig']`.
>
> </p></details>

### [config](config) / [base.py](base.py)
> <details><summary><code>class BaseConfig</code> - Abstract marker interface for all configuration entities.</summary><p>
>
> A base class used to unify all configuration dataclasses under a single type hierarchy. Currently acts as a marker interface, allowing type checkers and dependency injection containers to identify configuration objects without adding runtime overhead.
>
> 🔴 `__init__()`: [None](#basepy) - Default constructor. Intended to be inherited by concrete `@dataclass` implementations.
>
> *Note: This class intentionally contains no methods or serialization logic (like `to_dict()`) to maintain strict separation of concerns. Serialization is handled exclusively by the `infrastructure` layer.*
>
> </p></details>

### [config](config) / [model.py](model.py)
> <details><summary><code>class ModelConfig</code> - Represents configuration parameters for a single AI model.</summary><p>
>
> An immutable container defining the identity of a model to be benchmarked. Used as a building block within `BenchmarkCase`.
>
> 🔴 `__init__()`: [None](#modelpy) - Initializes the dataclass with model family and size.  
> 🔴 `size`: [str](#modelpy) - _Property_ for the model size variant (e.g., "n", "s", "m", "l", "x").  
> 🔴 `family`: [str](#modelpy) - _Property_ for the model architecture family (e.g., "yolov8", "yolov11", "prism").  
> 🔴 `name`: [str](#modelpy) - _Computed property_ returning the concatenated identifier (e.g., "yolov8n").  
>
> </p></details>

### [config](config) / [benchmark.py](benchmark.py)
> <details><summary><code>class BenchmarkCase</code> - Represents a single benchmark execution scenario.</summary><p>
>
> An immutable container grouping a set of models to be tested together in a single run context. Renamed from `BenchmarkRun` to adhere to domain-driven design naming conventions (entities should be nouns, not verbs).
>
> 🔴 `__init__()`: [None](#benchmarkpy) - Initializes the dataclass with a tuple of models.  
> 🔴 `models`: [tuple[ModelConfig, ...]](#benchmarkpy) - _Property_ containing the models to be executed in this scenario.  
> 🔴 `model_names`: [tuple[str, ...]](#benchmarkpy) - _Computed property_ returning a tuple of formatted model names for logging and reporting.  
>
> </p></details>

> <details><summary><code>class BenchmarkConfig</code> - Represents global parameters for the benchmark execution engine.</summary><p>
>
> An immutable container defining the operational constraints and environment settings for the benchmark suite. Aggregates multiple `BenchmarkCase` instances and applies global settings like device targeting and iteration counts.
>
> 🔴 `__init__()`: [None](#benchmarkpy) - Initializes the dataclass with scenarios and global parameters.  
> 🔴 `runs`: [tuple[BenchmarkCase, ...]](#benchmarkpy) - _Property_ containing the execution scenarios. (Note: Field name kept as `runs` for backward compatibility with existing YAML schemas).  
> 🔴 `formats`: [tuple[str, ...]](#benchmarkpy) - _Property_ defining target export formats (e.g., "pytorch", "onnx", "tensorrt").  
> 🔴 `quantization`: [tuple[str, ...]](#benchmarkpy) - _Property_ defining target quantization levels (e.g., "fp32", "fp16", "int8").  
> 🔴 `task_type`: [TaskType | None](#benchmarkpy) - _Property_ specifying the YOLO task type (e.g., DETECT, SEGMENT).  
> 🔴 `device_type`: [DeviceType | None](#benchmarkpy) - _Property_ specifying the target hardware device (e.g., CUDA, CPU).  
> 🔴 `input_size`: [int | None](#benchmarkpy) - _Property_ for the inference image resolution (e.g., 640).  
> 🔴 `batch_size`: [int | None](#benchmarkpy) - _Property_ for the inference batch size.  
> 🔴 `warmup_iterations`: [int | None](#benchmarkpy) - _Property_ for the number of warmup passes before timing.  
> 🔴 `main_iterations`: [int | None](#benchmarkpy) - _Property_ for the number of timed execution passes.  
> 🔴 `confidence_threshold`: [float | None](#benchmarkpy) - _Property_ for the minimum detection confidence score.  
> 🔴 `test_images`: [str | None](#benchmarkpy) - _Property_ for the path to the validation dataset.  
>
> </p></details>

### [config](config) / [system.py](system.py)
> <details><summary><code>class SystemInfoConfig</code> - Represents toggles for hardware telemetry collection.</summary><p>
>
> An immutable container defining which hardware metrics should be polled during the benchmark execution. Allows fine-grained control over performance overhead vs. data granularity.
>
> 🔴 `__init__()`: [None](#systempy) - Initializes the dataclass with boolean toggles.  
> 🔴 `collect_gpu`: [bool](#systempy) - _Property_ enabling GPU utilization and VRAM monitoring.  
> 🔴 `collect_power`: [bool](#systempy) - _Property_ enabling power consumption monitoring (CPU/GPU wattage).  
> 🔴 `collect_temperature`: [bool](#systempy) - _Property_ enabling thermal monitoring (CPU/GPU Celsius).  
>
> </p></details>

### [config](config) / [report.py](report.py)
> <details><summary><code>class ReportConfig</code> - Represents settings for output generation and persistence.</summary><p>
>
> An immutable container defining where and how benchmark results should be saved. Decoupled from the actual file I/O logic, which is handled by infrastructure reporters.
>
> 🔴 `__init__()`: [None](#reportpy) - Initializes the dataclass with output parameters.  
> 🔴 `directory`: [Path](#reportpy) - _Property_ specifying the target directory for report generation.  
> 🔴 `formats`: [tuple[str, ...]](#reportpy) - _Property_ defining output formats (e.g., "json", "csv", "markdown").  
> 🔴 `use_timestamp`: [bool](#reportpy) - _Property_ indicating whether to append a timestamp to output filenames.  
>
> </p></details>

### [config](config) / [root.py](root.py)
> <details><summary><code>class Config</code> - The root aggregate combining all configuration sections.</summary><p>
>
> The top-level immutable container representing the complete application state. Acts as the single entry point for dependency injection, providing runners and collectors with access to benchmark, system, and reporting parameters.
>
> 🔴 `__init__()`: [None](#rootpy) - Initializes the dataclass with nested configuration sections.  
> 🔴 `benchmark`: [BenchmarkConfig | None](#rootpy) - _Property_ containing the benchmark execution parameters.  
> 🔴 `system_info`: [SystemInfoConfig | None](#rootpy) - _Property_ containing the hardware telemetry toggles.  
> 🔴 `output`: [ReportConfig](#rootpy) - _Property_ containing the output generation settings.  
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values)  
🔴 **NONE** - No tests written yet (Stubs or pending implementation)