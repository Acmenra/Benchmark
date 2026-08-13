# Quantization Exceptions Module Documentation

## Overview

The **quantization** module within the `infrastructure/exceptions` package represents the specialized error handling layer for model export and quantization pipelines within the Edge AI Benchmark Suite. Engineered following Clean Architecture principles, it provides a strict, granular, and type-safe exception hierarchy for capturing and propagating failures during model conversion, calibration, and runtime format generation.

This module acts as the **domain-specific error registry** for the model preparation pipeline. It decouples the underlying third-party export engines (Ultralytics, ONNX Runtime, OpenVINO, TensorRT, NCNN, PyTorch) from the core benchmark runner by translating generic engine crashes into meaningful, actionable domain exceptions.

This module contains 7 core exception entities (all inheriting from `ModelError`):
- **CalibrationDataError**: Raised when calibration datasets (e.g., `data.yaml` for INT8) are missing or invalid.
- **ModelExportError**: Raised when the base model export to an intermediate or final runtime format fails.
- **ONNXQuantizationError**: Raised during ONNX graph export or INT8 quantization.
- **OpenVINOQuantizationError**: Raised during OpenVINO IR conversion or Post-Training Quantization (PTQ).
- **PyTorchQuantizationError**: Raised during native PyTorch dynamic/static quantization.
- **TensorRTQuantizationError**: Raised during TensorRT engine building or FP16/INT8 calibration.
- **NCNNQuantizationError**: Raised during NCNN export or INT8 histogram calibration.

All components are implemented as standard Python exception classes inheriting from `ModelError`, ensuring:
-  Granular error handling (e.g., catching only `TensorRTQuantizationError` without masking other model errors).
-  Strict integration with the benchmark runner's `try...except` blocks for graceful degradation (e.g., skipping unsupported formats instead of crashing).
-  Clear, actionable error messages for debugging export pipeline failures.

---

### Folder structure

|-> `quantization/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Module exports and public API definition. [Learn more.](#__init__py)  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `errors.py` - Specific exception classes for export and quantization failures. [Learn more.](#errorspy)

---

### [quantization](quantization) / [__init__.py](__init__.py)
> <details><summary><code>Module Exports</code> - Public API definition for the quantization exceptions.</summary><p>
>
> Exposes the core exception classes to the rest of the application, ensuring clean import paths (e.g., `from infrastructure.exceptions.quantization import TensorRTQuantizationError`).
>
> 🔴 `__all__`: [List[str]](#__init__py) - Explicitly defines the public API: `['CalibrationDataError', 'ModelExportError', 'NCNNQuantizationError', 'ONNXQuantizationError', 'OpenVINOQuantizationError', 'PyTorchQuantizationError', 'TensorRTQuantizationError']`. 
>
> </p></details>

### [quantization](quantization) / [errors.py](errors.py)

> <details><summary><code>class CalibrationDataError</code> - Exception raised when calibration data preparation fails.</summary><p>
>
> Inherits from `ModelError`. Triggered when the benchmark runner attempts to prepare INT8 quantization but lacks the required calibration dataset.
>
> 🔴 `__init__()`: [None](#errorspy) - Initializes the exception with a descriptive error message.  
> 🔴 **Raised when**: 
> - The `data.yaml` configuration file for INT8 calibration is missing.
> - The calibration dataset path is invalid or contains no valid images.
>
> </p></details>

> <details><summary><code>class ModelExportError</code> - Exception raised when exporting a model to a runtime format fails.</summary><p>
>
> Inherits from `ModelError`. Acts as a catch-all for base export failures before specific engine errors are triggered.
>
> 🔴 `__init__()`: [None](#errorspy) - Initializes the exception.  
> 🔴 **Raised when**: 
> - The underlying export engine (e.g., Ultralytics export, ONNX exporter) throws an error or produces an invalid file.
> - The target format is incompatible with the model architecture.
>
> </p></details>

> <details><summary><code>class ONNXQuantizationError</code> - Exception raised during ONNX model quantization or export.</summary><p>
>
> Inherits from `ModelError`. Specific to the ONNX ecosystem.
>
> 🔴 `__init__()`: [None](#errorspy) - Initializes the exception.  
> 🔴 **Raised when**: 
> - ONNX Runtime quantization fails (e.g., unsupported opset, missing operators).
> - The exported ONNX graph is invalid or corrupted.
>
> </p></details>

> <details><summary><code>class OpenVINOQuantizationError</code> - Exception raised during OpenVINO model conversion or quantization.</summary><p>
>
> Inherits from `ModelError`. Specific to the Intel OpenVINO toolkit.
>
> 🔴 `__init__()`: [None](#errorspy) - Initializes the exception.  
> 🔴 **Raised when**: 
> - The OpenVINO Model Optimizer fails to convert the source model.
> - Post-Training Quantization (PTQ) fails due to calibration data issues.
>
> </p></details>

> <details><summary><code>class PyTorchQuantizationError</code> - Exception raised during PyTorch model quantization.</summary><p>
>
> Inherits from `ModelError`. Specific to native PyTorch quantization workflows.
>
> 🔴 `__init__()`: [None](#errorspy) - Initializes the exception.  
> 🔴 **Raised when**: 
> - Dynamic or static quantization via `torch.quantization` fails.
> - The model architecture contains layers unsupported by the PyTorch quantization engine.
>
> </p></details>

> <details><summary><code>class TensorRTQuantizationError</code> - Exception raised during TensorRT engine building or quantization.</summary><p>
>
> Inherits from `ModelError`. Specific to the NVIDIA TensorRT engine.
>
> 🔴 `__init__()`: [None](#errorspy) - Initializes the exception.  
> 🔴 **Raised when**: 
> - The TensorRT builder fails to parse the ONNX model.
> - INT8/FP16 calibration fails due to missing CUDA support or invalid calibration cache.
>
> </p></details>

> <details><summary><code>class NCNNQuantizationError</code> - Exception raised during NCNN model export or INT8 quantization.</summary><p>
>
> Inherits from `ModelError`. Specific to the Tencent NCNN framework.
>
> 🔴 `__init__()`: [None](#errorspy) - Initializes the exception.  
> 🔴 **Raised when**: 
> - The `onnx2ncnn` conversion tool fails or is not installed.
> - NCNN INT8 calibration fails due to invalid histogram generation.
>
> </p></details>

---

### Testing Status Legend
🟢 **FULL** - Comprehensive tests (DDT, mocks, edge cases, negative paths, serialization checks)  
🟡 **PARTIAL** - Tests exist but need improvement (e.g., missing edge cases for `None` values)  
🔴 **NONE** - No tests written yet (Stubs, pending implementation, or untested domain entities)