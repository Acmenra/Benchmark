# Infrastructure Exceptions Module Documentation

## Overview

The **exceptions** module within the `infrastructure` package represents the centralized error handling layer for the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides a strict, hierarchical, and type-safe exception registry for capturing, propagating, and gracefully handling failures across the configuration, dataset, and model preparation pipelines.

This module acts as the **domain-specific error boundary** for the infrastructure layer. It decouples low-level system failures (e.g., malformed YAML, missing directories, engine crashes) from the core application logic by translating generic Python exceptions into meaningful, actionable domain exceptions. This enables the benchmark runner to implement graceful degradation (e.g., skipping a failed model export instead of crashing the entire suite).

This module contains 4 core base exception entities:
- **RaBenchmarkException**: The root exception for all benchmark-specific errors.
- **ConfigError**: Raised during YAML parsing or Pydantic schema validation failures.
- **DatasetError**: Raised when dataset paths are invalid, missing, or lack required structure.
- **ModelError**: The base class for all model lifecycle errors (loading, inference, export), serving as the parent for specialized sub-modules like `quantization`.

All components are implemented as standard Python exception classes, ensuring:
-  **Hierarchical Catching**: Ability to catch broad categories (e.g., `except ModelError`) or specific failures (e.g., `except OpenVINOQuantizationError`).
-  **Graceful Degradation**: Seamless integration with the runner's `try...except` blocks to log errors and skip unsupported configurations.
-  **Clear Diagnostics**: Actionable error messages for debugging infrastructure and pipeline failures.

---

### Folder structure

|-> `exceptions/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Public API definition and module exports. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `base.py` - Root and domain-level base exceptions. [Learn more.](#basepy)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `quantization/` - Specialized export and quantization error hierarchy. [Learn more.](quantization/README.md)

---

### [exceptions](exceptions) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the infrastructure exceptions.</summary><p>
>
> Exposes the core exception classes to the rest of the application, ensuring clean import paths (e.g., `from infrastructure.exceptions import ConfigError, TensorRTQuantizationError`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['RaBenchmarkException', 'ConfigError', 'DatasetError', 'ModelError', 'CalibrationDataError', 'ModelExportError', 'NCNNQuantizationError', 'ONNXQuantizationError', 'OpenVINOQuantizationError', 'PyTorchQuantizationError', 'TensorRTQuantizationError']`. 
>
> </p></details>

---

### [exceptions](exceptions) / [base.py](base.py)

> <details><summary><code>class RaBenchmarkException</code> - Root exception for all benchmark-related errors.</summary><p>
>
> Inherits directly from Python's built-in `Exception`. Acts as the ultimate base class for any custom error raised within the benchmark suite, allowing top-level handlers to catch all benchmark-specific failures without masking standard Python errors (like `KeyboardInterrupt`).
>
> 🔴 `__init__()`: [None](#basepy) - Initializes the root exception.  
>
> </p></details>

> <details><summary><code>class ConfigError</code> - Exception raised for configuration validation or parsing errors.</summary><p>
>
> Inherits from `RaBenchmarkException`. Triggered during the initialization phase when the system attempts to load and validate the YAML configuration file.
>
> 🔴 `__init__()`: [None](#basepy) - Initializes the exception with a descriptive validation error.  
> 🔴 **Raised when**: 
> - The YAML configuration file is malformed, missing, or lacks required fields.
> - Provided values fail Pydantic schema validation (e.g., invalid device type, unsupported quantization level).
>
> </p></details>

> <details><summary><code>class DatasetError</code> - Exception raised for dataset loading or validation errors.</summary><p>
>
> Inherits from `RaBenchmarkException`. Triggered when the benchmark runner attempts to locate and validate the calibration or validation dataset.
>
> 🔴 `__init__()`: [None](#basepy) - Initializes the exception.  
> 🔴 **Raised when**: 
> - The specified dataset path does not exist or is not a directory.
> - The dataset lacks required structural files (e.g., `data.yaml`, `images/` directory).
>
> </p></details>

> <details><summary><code>class ModelError</code> - Base exception for all model-related errors.</summary><p>
>
> Inherits from `RaBenchmarkException`. Acts as the foundational base class for any failure occurring during the model lifecycle (loading, inference, export, quantization). Specialized sub-modules (like `quantization`) inherit from this class to provide granular error tracking.
>
> 🔴 `__init__()`: [None](#basepy) - Initializes the model error.  
> 🔴 **Design Note**: 
> - Catching `ModelError` in the runner will gracefully skip the current model/format combination and proceed to the next benchmark case.
> - Specific engine failures (e.g., `TensorRTQuantizationError`) inherit from this class.
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values)  
🔴 **NONE** - No tests written yet (Stubs, pending implementation, or structural domain entities)