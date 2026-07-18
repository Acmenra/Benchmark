# application/benchmark/runner.py

import glob
import logging
import os
from pathlib import Path

import cv2
import numpy as np
import torch
from acmenra_cv import YOLOBackend
from ultralytics import YOLO

from application.benchmark.metrics.collector import MetricsCollector
from core.entities.config import BenchmarkConfig, BenchmarkRun
from core.entities.metrics import ModelBenchmarkResult
from core.enums.model import Coco, DeviceType, TaskType, export_extension, ultralytics_export_format

logger = logging.getLogger(__name__)


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
                model_path = self.resolve_model_path(family, size, format_)
                if model_path is None:
                    logger.warning("Формат %s для %s%s недоступен — пропуск", format_, family, size)
                    continue

                collector = MetricsCollector(case)
                model = self._build_yolo_backend(model_path)

                try:
                    self._warmup(model)
                    collector.start_run()
                    self._run_model_on_images(model, image_paths, collector)
                finally:
                    collector.stop_run()

                raw_result = collector.get()
                results.append(
                    ModelBenchmarkResult(
                        model={
                            "family": family,
                            "size": size,
                            "format": format_,
                        },
                        performance=raw_result.performance,
                        cpu=raw_result.cpu,
                        gpu=raw_result.gpu,
                    )
                )

        return results

    def _get_dataset_path(self) -> Path:
        if self.benchmark_config.test_images is None:
            raise ValueError("benchmark.test_images is required for benchmark run")

        dataset_path = Path(self.benchmark_config.test_images)
        if not dataset_path.is_dir():
            raise ValueError(f"Dataset path not found: {dataset_path}")
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

    def resolve_model_path(self, family: str, size: str, format_: str) -> Path | None:
        """Возвращает путь к модели нужного формата.

        Для pytorch — прямой путь к .pt. 
        Для остальных форматов:
        если артефакт уже существует на диске — вернуть его; иначе
        сконвертировать через YOLO.export() и вернуть путь к результату.
        Возвращает None, если формат неизвестен или экспорт не удался.
        """
        if format_ == "pytorch":
            return Path(f"{family}{size}.pt")

        export_format = ultralytics_export_format(format_)
        extension = export_extension(format_)
        if export_format is None or extension is None:
            logger.warning("Неизвестный формат модели: %s", format_)
            return None

        cached = self._find_cached_artifact(family, size, extension)
        if cached is not None:
            logger.info("Найден закэшированный артефакт %s: %s", format_, cached)
            return cached

        pt_path = Path(f"{family}{size}.pt")
        logger.info("Экспорт %s%s -> %s", family, size, format_)
        try:
            exported = YOLO(str(pt_path)).export(format=export_format)
        except Exception:
            logger.exception("Не удалось экспортировать %s в формат %s", pt_path, format_)
            return None

        exported_path = Path(exported)
        if not exported_path.exists():
            logger.error("Экспорт %s завершился без файла: %s", format_, exported_path)
            return None

        logger.info("Экспорт завершён: %s", exported_path)
        return exported_path

    def _find_cached_artifact(self, family: str, size: str, extension: str) -> Path | None:
        """Найти ранее экспортированный артефакт модели по расширению."""
        candidate = Path(f"{family}{size}{extension}")
        return candidate if candidate.exists() else None

    def _build_yolo_backend(self, model_path: Path) -> YOLOBackend:
        device = self._normalize_device(self.benchmark_config.device_type)
        return YOLOBackend(
            model=YOLO(str(model_path), task=TaskType.DETECT.value),
            device=device,
            category=Coco,
            task_type=TaskType.DETECT,
            threshold=self.benchmark_config.confidence_threshold or 0.25,
            iou=0.7,
            imgsz=self.benchmark_config.input_size or 640,
            half=False,
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

    def _warmup(self, backend: YOLOBackend) -> None:
        input_size = self.benchmark_config.input_size or 640
        warmup_iterations = self.benchmark_config.warmup_iterations or 10
        fake_frame = np.zeros((input_size, input_size, 3), dtype=np.uint8)
        for _ in range(warmup_iterations):
            backend.predict(fake_frame)
