# core/domain/config/benchmark.py

import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional, List

from core.domain.config.base import BaseConfig
from core.domain.config.model import ModelConfig
from core.enums.model import DeviceType, TaskType


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class BenchmarkCase(BaseConfig):
    """
    Configuration for a single benchmark scenario (run).

    Represents a specific combination of models to be evaluated together
    under identical hardware and runtime conditions. Previously named
    `BenchmarkRun`, renamed to reflect that it is a noun (a scenario)
    rather than a verb (an action).

    Attributes:
        models (tuple[ModelConfig, ...]): Immutable sequence of models to benchmark in this case.
    """
    models: tuple[ModelConfig, ...]

    @property
    def model_names(self) -> tuple[str, ...]:
        """
        Retrieves the formatted names of all models in this benchmark case.

        Returns:
            tuple[str, ...]: A tuple of model names in "family-size" format.
        """
        return tuple(model.name for model in self.models)


@dataclass(slots=True, frozen=True)
class BenchmarkConfig(BaseConfig):
    """
    Global configuration for the benchmark execution engine.

    Aggregates all scenarios (cases) and defines the global parameters
    that apply across the entire benchmark suite, such as target devices,
    quantization levels, and input dimensions.

    Attributes:
        runs (tuple[BenchmarkCase, ...]): Sequence of benchmark scenarios to execute.
        models_dir (Path): Directory path where model weights and cached artifacts are stored.
        run_validation (bool): Flag indicating whether to compute quality metrics (mAP, etc.).
        formats (tuple[str, ...]): Target inference formats (e.g., 'onnx', 'openvino', 'tensorrt').
        quantization (tuple[str, ...]): Target quantization levels (e.g., 'fp32', 'fp16', 'int8').
        task_type (TaskType | None): The computer vision task (e.g., detect, segment).
        devices (tuple[DeviceType, ...] | None): Target hardware devices for execution.
        input_size (int | None): Spatial resolution for model input (e.g., 640).
        batch_size (int | None): Number of images processed simultaneously.
        warmup_iterations (int | None): Number of initial inference passes to stabilize performance.
        main_iterations (int | None): Number of measured inference passes for statistics.
        confidence_threshold (float | None): Minimum confidence score for detection filtering.
        test_images (str | None): Path to the validation dataset or synthetic data directive.

    Note:
        - All tuple fields are immutable to prevent accidental modification during execution.
        - If `run_validation` is False, quality metrics collection is skipped to save time.
    """
    runs: tuple[BenchmarkCase, ...]
    models_dir: Path
    run_validation: bool = True
    formats: tuple[str, ...] = ()
    quantization: tuple[str, ...] = ()
    task_type: TaskType | None = None
    devices: tuple[DeviceType, ...] | None = None
    input_size: int | None = None
    batch_size: int | None = None
    warmup_iterations: int | None = None
    main_iterations: int | None = None
    confidence_threshold: float | None = None
    test_images: str | None = None

