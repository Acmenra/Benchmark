# Infrastructure: Model Quantization Module

## Overview

The **model_quantization** module is responsible for converting standard PyTorch (`.pt`) YOLO models into optimized, hardware-specific runtime formats (ONNX, OpenVINO, TensorRT, NCNN, PyTorch INT8). 

Following Clean Architecture principles, this module isolates all vendor-specific quantization logic from the core benchmarking pipeline. It provides a unified interface (`quantize()`) for each target format, handling fallback mechanisms, calibration data preparation, and graceful degradation if specific hardware tools are unavailable.

---

## Folder Structure

|-> `model_quantization/`  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `__init__.py` - Public API exports for all quantizers.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `calibration.py` - Core logic for parsing Ultralytics `data.yaml` and preprocessing calibration images.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `yolo_export.py` - Base wrapper for standard Ultralytics model exporting and downloading.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `onnx.py` - ONNX Runtime static INT8 quantization implementation.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `openvino.py` - OpenVINO FP16 compression and NNCF INT8 quantization.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `tensorrt.py` - NVIDIA TensorRT FP16/INT8 engine building with custom entropy calibrators.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `pytorch.py` - Native PyTorch dynamic INT8 quantization.  
&nbsp;&nbsp;&nbsp;&nbsp; ∟ `ncnn.py` - NCNN FP32 export and INT8 quantization via CLI tool wrappers.  

---

## Core Components

### [calibration.py](calibration.py)
> <details><summary><code>Calibration Data Pipeline</code></summary><p>
> Handles the extraction and preprocessing of images required for INT8 quantization.
> 
> 🔴 `collect_calibration_images()`: Parses `data.yaml`, resolves relative/absolute paths (including lazy `../` paths), and returns up to `max_samples` image paths.  
> 🔴 `preprocess_yolo_image()`: Converts images to RGB, resizes to `input_size`, normalizes to `[0, 1]`, and transposes to `NCHW` format, matching YOLO's expected input tensor.
> </p></details>

### [yolo_export.py](yolo_export.py)
> <details><summary><code>Base Export Utilities</code></summary><p>
> Ensures the base `.pt` model is available and handles the initial export step.
> 
> 🔴 `ensure_yolo_pt_model()`: Downloads the official Ultralytics `.pt` weights if they are missing locally.  
> 🔴 `export_yolo_model()`: Wraps `ultralytics.YOLO.export()`, ensuring the output artifact is moved to the expected cached directory structure.
> </p></details>

---

## Format-Specific Quantizers

### [onnx.py](onnx.py)
> <details><summary><code>ONNXINT8Quantizer</code></summary><p>
> Performs static INT8 quantization using `onnxruntime.quantization`.
> 
> 🔴 **Mechanism**: Exports FP32 ONNX → Creates `YoloONNXCalibrationDataReader` → Runs `quantize_static` with `QuantFormat.QDQ` and per-channel MinMax calibration.  
> 🔴 **Dependencies**: `onnx`, `onnxruntime`.
> </p></details>

### [openvino.py](openvino.py)
> <details><summary><code>OpenVINOFP16Quantizer</code> & <code>OpenVINOINT8Quantizer</code></summary><p>
> Optimizes models for Intel CPUs, GPUs, and VPUs.
> 
> 🔴 **FP16**: Reads the FP32 OpenVINO IR (`.xml`) and saves it with `compress_to_fp16=True`.  
> 🔴 **INT8**: Uses Intel NNCF (`nncf.quantize`) with a post-training quantization (PTQ) dataset built from preprocessed calibration images.
> 🔴 **Dependencies**: `openvino`, `nncf`.
> </p></details>

### [tensorrt.py](tensorrt.py)
> <details><summary><code>TensorRTFP16Quantizer</code> & <code>TensorRTINT8Quantizer</code></summary><p>
> Builds highly optimized NVIDIA TensorRT `.engine` files.
> 
> 🔴 **Mechanism**: Exports to ONNX → Parses with `trt.OnnxParser` → Builds engine with `trt.BuilderFlag.FP16` or `trt.BuilderFlag.INT8`.  
> 🔴 **INT8 Calibration**: Implements a custom `trt.IInt8EntropyCalibrator2` that feeds preprocessed batches directly to the GPU via `trt.cuda.memcpy_host_to_device`.  
> 🔴 **Dependencies**: `tensorrt` (Requires NVIDIA GPU and CUDA).
> </p></details>

### [pytorch.py](pytorch.py)
> <details><summary><code>PyTorchINT8Quantizer</code></summary><p>
> Applies native PyTorch dynamic quantization.
> 
> 🔴 **Mechanism**: Loads the model to CPU, applies `torch.ao.quantization.quantize_dynamic` targeting `Linear` and `Conv2d` layers with `torch.qint8`. Does not require a calibration dataset (dynamic per-tensor quantization).  
> 🔴 **Dependencies**: `torch>=1.13`.
> </p></details>

### [ncnn.py](ncnn.py)
> <details><summary><code>NCNNFP32Exporter</code> & <code>NCNNINT8Quantizer</code></summary><p>
> Targets ARM-based Edge devices (Raspberry Pi, Orange Pi) via the NCNN framework.
> 
> 🔴 **FP32**: Exports to ONNX, then invokes the `onnx2ncnn` CLI tool.  
> 🔴 **INT8**: Creates symlinks for calibration images → Invokes `ncnn2table` (with YOLO-specific `mean=[0,0,0]` and `norm=[0.0039...]`) → Invokes `ncnn2int8` to generate `.param` and `.bin` files.  
> 🔴 **Dependencies**: System-level `ncnn-tools` (`onnx2ncnn`, `ncnn2table`, `ncnn2int8` must be in `$PATH`).
> </p></details>

---

## Design Principles

1. **Idempotency**: All `quantize()` and `export()` methods check if the target artifact already exists (`if target_path.exists(): return target_path`). This prevents redundant, time-consuming re-computation during benchmark retries.
2. **Graceful Degradation**: If a required package (e.g., `tensorrt` on a Mac) or CLI tool (e.g., `ncnn2table`) is missing, the quantizer raises a specific `*QuantizationError`. The `BenchmarkRunner` catches this and marks the configuration as `skipped` without crashing the entire suite.
3. **Unified Calibration**: All INT8 quantizers rely on the single `calibration.py` module, ensuring consistent image preprocessing (BGR→RGB, resize, normalize, NCHW) across all hardware backends.

---

## Testing Status Legend
🟢 **FULL** - Comprehensive tests (mocked subprocess calls, DDT for path resolution, quantization output validation)  
🟡 **PARTIAL** - Basic happy-path tests exist, but edge cases (e.g., missing CLI tools, corrupted YAML) need more coverage  
🔴 **NONE** - No tests written yet