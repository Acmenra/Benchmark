"""Перечисления предметной области Edge AI Benchmark Suite."""

from enum import StrEnum


class ModelFormat(StrEnum):
    """Формат представления модели детекции объектов."""

    PYTORCH = "pytorch"
    ONNX = "onnx"
    TENSORRT = "tensorrt"
    OPENVINO = "openvino"


class PlatformType(StrEnum):
    """Тип платформы, на которой выполняется бенчмарк."""

    DESKTOP = "desktop"
    JETSON = "jetson"
    RASPBERRY_PI = "raspberry_pi"
    UNKNOWN = "unknown"


class ReportFormat(StrEnum):
    """Формат экспорта результатов бенчмарка."""

    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    HTML = "html"


class ModelSource(StrEnum):
    """Откуда берётся вес модели."""

    BUILTIN = "builtin"
    """Стандартное имя вида ``yolov8n``, разрешаемое ultralytics/локальным кэшем."""

    LOCAL = "local"
    """Локальный чекпоинт по произвольному пути на диске."""

    HUGGINGFACE = "huggingface"
    """Модель, скачиваемая с Hugging Face Hub (repo_id + filename)."""


class Precision(StrEnum):
    """Точность представления весов модели при экспорте/инференсе."""

    FP32 = "fp32"
    FP16 = "fp16"
    """Половинная точность — быстрее на GPU/OpenVINO, без калибровки, потеря
    accuracy обычно незначительна."""
    INT8 = "int8"
    """Целочисленное квантование — быстрее всего, требует калибровочный
    датасет (см. `BenchmarkConfig.accuracy_dataset`), заметнее теряет accuracy."""
