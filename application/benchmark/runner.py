# application/benchmark/runner.py

import glob
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
from acmenra_cv import YOLOBackend
from ultralytics import YOLO

from application.benchmark.metrics.collector import MetricsCollector
from core.entities.config import BenchmarkConfig, BenchmarkRun
from core.entities.metrics import ModelBenchmarkResult, QualityMetrics
from core.enums.model import (
    Coco,
    DeviceType,
    QuantizationLevel,
    TaskType,
    export_extension,
    ultralytics_export_format,
)
from infrastructure.metrics.quality import YOLOQualityMetricsCollector

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ResolvedModelArtifact:
    """Фактически выбранный артефакт модели после export/fallback."""

    path: Path
    quantization: str
    fallback_from: str | None = None


class BenchmarkRunner:
    """Координирует загрузку модели, инференс и сбор метрик."""

    def __init__(self, benchmark_config: BenchmarkConfig) -> None:
        self.benchmark_config = benchmark_config

    def run_suite(self) -> list[ModelBenchmarkResult]:
        """Запустить все benchmark-кейсы и вернуть результаты по моделям."""
        all_results: list[ModelBenchmarkResult] = []
        for case in self.benchmark_config.runs:
            case_results = self._run_case(case)
            all_results.extend(case_results)
        return all_results

    def _run_case(self, case: BenchmarkRun) -> list[ModelBenchmarkResult]:
        dataset_path = self._get_dataset_path()
        image_paths = self._collect_image_paths(dataset_path)

        results: list[ModelBenchmarkResult] = []
        for model_config in case.models:
            family = model_config.family
            size = model_config.size

            for format_ in self._get_supported_formats():
                for quantization in self._get_quantization_levels():
                    artifact = self.resolve_model_artifact(
                        family,
                        size,
                        format_,
                        quantization,
                    )
                    if artifact is None:
                        logger.warning(
                            "Формат %s с квантованием %s для %s%s недоступен — пропуск",
                            format_,
                            quantization,
                            family,
                            size,
                        )
                        continue

                    collector = MetricsCollector(case)
                    model = self._build_yolo_backend(
                        artifact.path,
                        artifact.quantization,
                    )

                    try:
                        self._warmup(model)
                        collector.start_run()
                        self._run_model_on_images(model, image_paths, collector)
                    finally:
                        collector.stop_run()

                    raw_result = collector.get()

                    quality_metrics = self._collect_quality_metrics(model, family, size)

                    results.append(
                        ModelBenchmarkResult(
                            model={
                                "family": family,
                                "size": size,
                                "format": format_,
                                "quantization": artifact.quantization,
                                "requested_quantization": quantization,
                            },
                            performance=raw_result.performance,
                            cpu=raw_result.cpu,
                            gpu=raw_result.gpu,
                            quality=quality_metrics,
                        )
                    )

        return results

    def _get_dataset_path(self) -> Path:
        if self.benchmark_config.test_images is None:
            raise ValueError("benchmark.test_images is required for benchmark run")

        dataset_path = Path(self.benchmark_config.test_images)
        if not dataset_path.is_dir():
            raise ValueError(f"Dataset path not found: {dataset_path}")
        
        # Если в папке есть подпапка 'images/', используем её
        # (для структур где датасет содержит images/ и labels/)
        images_subdir = dataset_path / "images"
        if images_subdir.is_dir():
            return images_subdir
        
        return dataset_path

    def _collect_image_paths(self, dataset_path: Path) -> list[Path]:
        extensions = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
        image_paths: list[Path] = []

        for ext in extensions:
            image_paths.extend(Path(path) for path in glob.glob(os.path.join(dataset_path, f"*{ext}")))
            image_paths.extend(Path(path) for path in glob.glob(os.path.join(dataset_path, f"*{ext.upper()}")))

        if not image_paths:
            raise ValueError(f"No images found in {dataset_path}")

        return sorted(image_paths)

    def _get_supported_formats(self) -> tuple[str, ...]:
        return self.benchmark_config.formats or ("pytorch",)

    def _get_quantization_levels(self) -> tuple[str, ...]:
        return self.benchmark_config.quantization or (QuantizationLevel.FP32.value,)

    def _run_model_on_images(
        self,
        model: YOLOBackend,
        image_paths: list[Path],
        collector: MetricsCollector,
    ) -> None:
        main_iterations = self.benchmark_config.main_iterations or len(image_paths)

        for iteration in range(main_iterations):
            img_path = image_paths[iteration % len(image_paths)]
            frame = cv2.imread(str(img_path))
            if frame is None:
                logger.warning("Could not read %s, skipping", img_path)
                continue

            collector.mark_start()
            try:
                model.predict(frame)
            finally:
                collector.mark_stop()

    def resolve_model_artifact(
        self,
        family: str,
        size: str,
        format_: str,
        quantization: str = QuantizationLevel.FP32.value,
    ) -> ResolvedModelArtifact | None:
        """Вернуть модель нужного формата или fallback на fp32.

        Важно не подписывать fallback-артефакт как квантованный, иначе отчет
        будет показывать int8/fp16 там, где фактически запустилась fp32 модель.
        """
        requested_quantization = self._normalize_quantization(quantization)

        artifact = self._try_resolve_model_artifact(
            family,
            size,
            format_,
            requested_quantization,
        )
        if artifact is not None:
            return artifact

        if requested_quantization == QuantizationLevel.FP32.value:
            return None

        logger.warning(
            "Квантование %s для %s%s/%s недоступно, пробую fallback на fp32",
            requested_quantization,
            family,
            size,
            format_,
        )
        fallback_artifact = self._try_resolve_model_artifact(
            family,
            size,
            format_,
            QuantizationLevel.FP32.value,
        )
        if fallback_artifact is None:
            return None

        return ResolvedModelArtifact(
            path=fallback_artifact.path,
            quantization=fallback_artifact.quantization,
            fallback_from=requested_quantization,
        )

    def resolve_model_path(
        self,
        family: str,
        size: str,
        format_: str,
        quantization: str = QuantizationLevel.FP32.value,
    ) -> Path | None:
        """Backward-compatible wrapper: вернуть только путь к модели."""
        artifact = self.resolve_model_artifact(family, size, format_, quantization)
        return artifact.path if artifact is not None else None

    def _try_resolve_model_artifact(
        self,
        family: str,
        size: str,
        format_: str,
        quantization: str,
    ) -> ResolvedModelArtifact | None:
        """Возвращает путь к модели нужного формата.

        Для pytorch — прямой путь к .pt. 
        Для остальных форматов:
        если артефакт уже существует на диске — вернуть его; иначе
        сконвертировать через YOLO.export() и вернуть путь к результату.
        Возвращает None, если формат неизвестен или экспорт не удался.
        """
        quantization = self._normalize_quantization(quantization)
        if not self._is_quantization_supported(format_, quantization):
            return None

        if format_ == "pytorch":
            return ResolvedModelArtifact(
                path=Path(f"{family}{size}.pt"),
                quantization=quantization,
            )

        export_format = ultralytics_export_format(format_)
        extension = export_extension(format_)
        if export_format is None or extension is None:
            logger.warning("Неизвестный формат модели: %s", format_)
            return None

        cached = self._find_cached_artifact(family, size, extension, quantization)
        if cached is not None:
            logger.info(
                "Найден закэшированный артефакт %s/%s: %s",
                format_,
                quantization,
                cached,
            )
            return ResolvedModelArtifact(path=cached, quantization=quantization)

        pt_path = Path(f"{family}{size}.pt")
        export_kwargs = self._build_export_kwargs(export_format, quantization)
        if export_kwargs is None:
            return None

        logger.info("Экспорт %s%s -> %s/%s", family, size, format_, quantization)
        try:
            exported = YOLO(str(pt_path)).export(**export_kwargs)
        except Exception:
            logger.exception(
                "Не удалось экспортировать %s в формат %s/%s",
                pt_path,
                format_,
                quantization,
            )
            return None

        exported_path = Path(exported)
        if not exported_path.exists():
            logger.error("Экспорт %s завершился без файла: %s", format_, exported_path)
            return None

        target_path = self._build_cached_artifact_path(
            family,
            size,
            extension,
            quantization,
        )
        if target_path != exported_path:
            if target_path.exists():
                return target_path
            shutil.move(str(exported_path), str(target_path))
            exported_path = target_path

        logger.info("Экспорт завершён: %s", exported_path)
        return ResolvedModelArtifact(path=exported_path, quantization=quantization)

    def _is_quantization_supported(self, format_: str, quantization: str) -> bool:
        """Проверить, есть ли смысл пробовать квантование для формата."""
        if quantization == QuantizationLevel.FP32.value:
            return True

        unsupported_message = (
            "Квантование %s для формата %s сейчас не поддержано, будет fallback"
        )

        if format_ == "pytorch":
            # .pt остается исходным PyTorch-файлом; квантованный артефакт
            # появляется только после export в другой backend/format.
            logger.warning(unsupported_message, quantization, format_)
            return False

        if format_ == "openvino":
            # В текущей версии пайплайна OpenVINO export стабильно запускаем
            # только в fp32. Квантование вернем после отдельной проверки NNCF.
            logger.warning(unsupported_message, quantization, format_)
            return False

        if quantization == QuantizationLevel.INT4.value:
            logger.warning("INT4 пока не поддержан через Ultralytics export")
            return False

        supported_formats_by_quantization = {
            QuantizationLevel.FP16.value: {"onnx", "tensorrt"},
            QuantizationLevel.INT8.value: {"onnx", "tensorrt"},
        }
        supported_formats = supported_formats_by_quantization.get(quantization, set())
        if format_ not in supported_formats:
            logger.warning(unsupported_message, quantization, format_)
            return False

        return True

    def _find_cached_artifact(
        self,
        family: str,
        size: str,
        extension: str,
        quantization: str,
    ) -> Path | None:
        """Найти ранее экспортированный артефакт модели по расширению."""
        candidate = self._build_cached_artifact_path(
            family,
            size,
            extension,
            quantization,
        )
        return candidate if candidate.exists() else None

    def _build_cached_artifact_path(
        self,
        family: str,
        size: str,
        extension: str,
        quantization: str,
    ) -> Path:
        """Собрать имя export-артефакта с учётом уровня квантования."""
        if quantization == QuantizationLevel.FP32.value:
            return Path(f"{family}{size}{extension}")
        return Path(f"{family}{size}_{quantization}{extension}")

    def _build_export_kwargs(
        self,
        export_format: str,
        quantization: str,
    ) -> dict[str, object] | None:
        """Собрать параметры YOLO.export() для нужного уровня квантования."""
        export_kwargs: dict[str, object] = {"format": export_format}

        if quantization == QuantizationLevel.FP32.value:
            return export_kwargs

        if quantization == QuantizationLevel.FP16.value:
            export_kwargs["half"] = True
            return export_kwargs

        if quantization == QuantizationLevel.INT8.value:
            dataset_config_path = self._find_quality_dataset_config()
            if dataset_config_path is None:
                logger.warning(
                    "INT8 export требует data.yaml для калибровки, датасет не найден"
                )
                return None

            export_kwargs["int8"] = True
            export_kwargs["data"] = str(dataset_config_path)
            return export_kwargs

        return None

    def _normalize_quantization(self, quantization: str) -> str:
        """Нормализовать значение квантования из конфига."""
        try:
            return QuantizationLevel(quantization).value
        except ValueError:
            logger.warning("Неизвестный уровень квантования %s, используется fp32", quantization)
            return QuantizationLevel.FP32.value

    def _build_yolo_backend(
        self,
        model_path: Path,
        quantization: str = QuantizationLevel.FP32.value,
    ) -> YOLOBackend:
        device = self._normalize_device(self.benchmark_config.device_type)
        return YOLOBackend(
            model=YOLO(str(model_path), task=TaskType.DETECT.value),
            device=device,
            category=Coco,
            task_type=TaskType.DETECT,
            threshold=self.benchmark_config.confidence_threshold or 0.25,
            iou=0.7,
            imgsz=self.benchmark_config.input_size or 640,
            half=quantization == QuantizationLevel.FP16.value,
        )

    def _normalize_device(self, device_type: DeviceType | None) -> DeviceType:
        """Преобразует DeviceType enum в значение, поддерживаемое ultralytics.
        
        Значение 'auto' конвертируется в 'cpu' или 'cuda' в зависимости от доступности.
        """
        if device_type is None:
            return DeviceType.CPU
        
        device_str = device_type.value
        
        # Значения, которые ultralytics не поддерживает напрямую
        if device_str == 'auto':
            normalized = 'cuda' if torch.cuda.is_available() else 'cpu'
            return DeviceType(normalized)
        
        if device_str in ('npu', 'gpu', 'tpu', 'tensorrt', 'npu:rk3588', 'npu:intel', 'npu:hailo', 'tpu:coral'):
            logger.warning(f"Device '{device_str}' не поддерживается ultralytics, используется 'cpu'")
            return DeviceType.CPU
        
        return device_type

    def _collect_quality_metrics(
        self, model: YOLOBackend, family: str, size: str
    ) -> QualityMetrics | None:
        """Собирает метрики качества модели.
        
        Args:
            model: Загруженная модель для инференса.
            family: Семейство модели.
            size: Размер модели.
            
        Returns:
            QualityMetrics с рассчитанными метриками или None если сбор не удалось выполнить.
        """
        try:
            dataset_config_path = self._find_quality_dataset_config()

            if dataset_config_path is None:
                logger.debug(
                    "Датасет с разметкой не найден для %s%s, пропускаю сбор метрик качества",
                    family,
                    size,
                )
                return None

            logger.info("Собираю метрики качества для %s%s на датасете: %s", 
                       family, size, dataset_config_path)

            collector = YOLOQualityMetricsCollector(
                yolo_backend=model,
                dataset_path=dataset_config_path,
                imgsz=self.benchmark_config.input_size or 640,
                conf_threshold=self.benchmark_config.confidence_threshold or 0.25,
            )
            
            quality_metrics = collector.collect()
            return quality_metrics
            
        except Exception as e:
            logger.warning(
                "Не удалось собрать метрики качества для %s%s: %s",
                family,
                size,
                e,
            )
            return None

    def _find_quality_dataset_config(self) -> Path | None:
        """Найти YAML-конфиг датасета для Ultralytics validation."""
        validation_paths: list[Path] = []

        if self.benchmark_config.test_images is not None:
            benchmark_dataset_path = Path(self.benchmark_config.test_images)
            validation_paths.extend(
                [
                    benchmark_dataset_path / "data.yaml",
                    benchmark_dataset_path.parent / "data.yaml",
                ]
            )

        validation_paths.extend(
            [
                Path("dataset/data.yaml"),
                Path("dataset/val/data.yaml"),
                Path("dataset/validation/data.yaml"),
                Path("dataset/coco/data.yaml"),
                Path("data/val/data.yaml"),
            ]
        )

        for path in validation_paths:
            if path.is_file():
                return path

        return None

    def _warmup(self, backend: YOLOBackend) -> None:
        input_size = self.benchmark_config.input_size or 640
        warmup_iterations = self.benchmark_config.warmup_iterations or 10
        fake_frame = np.zeros((input_size, input_size, 3), dtype=np.uint8)
        for _ in range(warmup_iterations):
            backend.predict(fake_frame)
