# Infrastructure Config Module Documentation

## Overview

The **config** module within the `infrastructure` package represents the configuration loading, validation, and mapping layer of the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it acts as the boundary between external configuration sources (YAML files) and the pure, immutable domain models (`core.domain.config`).

This module implements the **DTO (Data Transfer Object) to Domain Model** pattern. It uses **Pydantic V2** for strict, fail-fast validation of raw dictionaries, ensuring that all types, ranges, and enum values are correct *before* any domain mapping occurs. This guarantees that the core benchmark runner and reporters operate exclusively on validated, type-safe data, completely decoupled from the underlying parsing library or file format.

This module contains 4 core components:
- **`config_reader.py`**: The entry point for loading YAML files and mapping validated Pydantic schemas into immutable domain dataclasses.
- **`configs_validator.py`**: A comprehensive Pydantic schema tree that enforces strict validation rules, enum checking, and structural integrity for the raw configuration dictionary.
- **`default_config.py`**: A factory function that generates a massive, full-matrix benchmark configuration programmatically, bypassing the need for a YAML file.
- **`ConfigError`**: A custom exception class for capturing and formatting configuration parsing or validation failures.

All components ensure:
- **Fail-fast validation**: Invalid YAML or unsupported enum values are caught immediately with clear, formatted error messages.
- **Domain isolation**: The core domain layer (`core.domain.config`) has zero dependencies on Pydantic or YAML parsers.
- **Type safety**: Complex nested structures (like lists of models and sizes) are safely transformed into tuples of domain objects.

---

### Folder structure

|-> `config/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module initialization and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `config_reader.py` - YAML loading and DTO-to-Domain mapping logic. [Learn more.](#config_readerpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `configs_validator.py` - Pydantic validation schemas for raw configuration data. [Learn more.](#configs_validatorpy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `default_config.py` - Programmatic default configuration factory. [Learn more.](#default_configpy)

---

### [config](config) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the infrastructure config package.</summary><p>
>
> Initializes the package. Currently, internal components are imported directly by the application entry point (`main.py`), but this module reserves the namespace for future public API exports.
>
> 🔴 `__all__`: [List[str]](#__init__py) - Currently empty `[]`. Reserved for explicit public API definition.
>
> </p></details>

---

### [config](config) / [config_reader.py](config_reader.py)
> <details><summary><code>function read_yaml()</code> - Loads and parses a YAML configuration file into a domain `Config` object.</summary><p>
>
> The main entry point for configuration loading. Reads raw YAML, delegates validation to `ConfigsValidator`, and maps the validated Pydantic schemas to immutable domain dataclasses.
>
> 🔴 `path`: [Path | str](#config_readerpy) - Path to the YAML configuration file.  
> 🔴 `Returns`: [Config](#config_readerpy) - Fully populated domain configuration object.  
> 🔴 `Raises`: `FileNotFoundError` if the file does not exist. `ConfigError` if YAML syntax is invalid.  
>
> </p></details>

> <details><summary><code>function _build_benchmark_config()</code> - Internal mapper from Pydantic schema to `BenchmarkConfig` domain model.</summary><p>
>
> Handles the complex transformation of nested lists and string enums into tuples of domain objects (e.g., `ModelConfig`, `BenchmarkCase`, `DeviceType`). Ensures paths are resolved to absolute `Path` objects.
>
> 🔴 `benchmark_data`: [Any](#config_readerpy) - Validated Pydantic `_BenchmarkConfigInputSchema` instance.  
> 🔴 `Returns`: [BenchmarkConfig](#config_readerpy) - Immutable domain configuration for the benchmark suite.  
>
> </p></details>

---

### [config](config) / [configs_validator.py](configs_validator.py)
> <details><summary><code>class ConfigsValidator</code> - Pydantic-based validation orchestrator for raw configuration dictionaries.</summary><p>
>
> Provides a strict, fail-fast validation layer using Pydantic V2. Ensures all required fields are present, types are correct, and enum values are valid before any domain mapping occurs.
>
> 🔴 `validate()`: [_ConfigInputSchema](#configs_validatorpy) - _Class method_ that takes a raw dictionary and returns a fully validated Pydantic schema tree.  
> 🔴 `_format_error()`: [str](#configs_validatorpy) - _Static method_ that extracts the first validation error and formats it into a human-readable string (e.g., `benchmark.devices: ...`).  
>
> </p></details>

> <details><summary><code>class _BenchmarkConfigInputSchema</code> - Pydantic schema for the core benchmark execution parameters.</summary><p>
>
> Validates the `benchmark` section of the YAML config. Enforces strict typing for iterations, thresholds, and validates enum lists for `devices`, `formats`, and `quantization`.
>
> 🔴 `runs`: [list[_BenchmarkRunInputSchema]](#configs_validatorpy) - List of model run scenarios.  
> 🔴 `models_dir`: [str | None](#configs_validatorpy) - Directory for caching model weights.  
> 🔴 `run_validation`: [bool](#configs_validatorpy) - Flag to enable/disable quality metrics (mAP) collection.  
> 🔴 `devices`: [list[str] | None](#configs_validatorpy) - Target hardware devices (validated against `DeviceType` enum).  
> 🔴 `formats`: [list[str]](#configs_validatorpy) - Target export formats (e.g., 'onnx', 'openvino').  
> 🔴 `quantization`: [list[str]](#configs_validatorpy) - Target quantization levels (validated against `QuantizationLevel` enum).  
> 🔴 `task_type`: [str | None](#configs_validatorpy) - CV task type (validated against `TaskType` enum).  
>
> </p></details>

> <details><summary><code>class _ModelInputSchema</code> - Pydantic schema for individual model definitions within a run.</summary><p>
>
> Validates the `family` (e.g., 'yolov8') and `sizes` (e.g., ['n', 's', 'm']) of a model. Ensures non-empty strings and proper stripping of whitespace.
>
> 🔴 `family`: [str](#configs_validatorpy) - Model architecture family.  
> 🔴 `sizes`: [list[str] | None](#configs_validatorpy) - List of model size variants.  
>
> </p></details>

> <details><summary><code>class _OutputInputSchema</code> - Pydantic schema for reporting and output persistence settings.</summary><p>
>
> Validates the `output` section, ensuring the target directory is specified and formats are valid strings. Handles timestamp normalization logic.
>
> 🔴 `directory`: [str](#configs_validatorpy) - Target directory for reports.  
> 🔴 `formats`: [list[str]](#configs_validatorpy) - Output formats (e.g., 'csv', 'json').  
> 🔴 `use_timestamp`: [bool](#configs_validatorpy) - Flag to append timestamp to output directory.  
>
> </p></details>

> <details><summary><code>class _SystemInfoInputSchema</code> - Pydantic schema for hardware telemetry collection flags.</summary><p>
>
> Validates the `system_info` section, providing boolean toggles for CPU, GPU, power, and temperature monitoring.
>
> 🔴 `collect_cpu`: [bool](#configs_validatorpy) - Enable CPU utilization/temperature polling.  
> 🔴 `collect_gpu`: [bool](#configs_validatorpy) - Enable GPU VRAM/utilization polling.  
> 🔴 `collect_power`: [bool](#configs_validatorpy) - Enable power draw monitoring.  
> 🔴 `collect_temperature`: [bool](#configs_validatorpy) - Enable thermal sensor reading.  
>
> </p></details>

> <details><summary><code>class ConfigError</code> - Custom exception for configuration parsing and validation failures.</summary><p>
>
> Inherits from `ValueError`. Raised when YAML syntax is invalid or Pydantic validation fails, providing a clear, formatted error message to the user.
>
> </p></details>

---

### [config](config) / [default_config.py](default_config.py)
> <details><summary><code>function build_default_config()</code> - Factory function for generating a comprehensive default `Config` without a YAML file.</summary><p>
>
> Iterates over all supported `ModelFamily` and `ModelSize` enums to generate a massive benchmark matrix. Useful for full-suite regression testing or when no explicit config is provided via CLI.
>
> 🔴 `Returns`: [Config](#default_configpy) - A fully populated domain configuration object with default paths and parameters.  
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values)  
🔴 **NONE** - No tests written yet (Stubs, pending implementation, or infrastructure layer)