# application/benchmark/runner.py

"""Слой оркестрации бенчмарка."""

import glob
import logging
import os
from pathlib import Path

import cv2
import numpy as np
from acmenra_cv import YOLOBackend
from ultralytics import YOLO

from application.benchmark.metrics.collector import MetricsCollector
from core.entities.config import BenchmarkConfig, BenchmarkRun
from core.entities.metrics import BenchmarkResult
from core.enums.model import Coco, DeviceType, TaskType

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Координирует загрузку модели, инференс и сбор метрик."""

    def __init__(self, benchmark_config: BenchmarkConfig) -> None:
        self.benchmark_config = benchmark_config

    def run_suite(self) -> list[BenchmarkResult]:
        results = []

        cases = self.benchmark_config.runs
        for case in cases:
            results.append(self._run_case(case))

        return results
        
    def _run_case(self, case: BenchmarkRun) -> BenchmarkResult:
        dataset_path = self._get_dataset_path()
        image_paths = self._collect_image_paths(dataset_path)
        collector = MetricsCollector(case)

        for model_config in case.models:
            family = model_config.family
            size = model_config.size

            for format_ in self._get_supported_formats():
                if format_ != "pytorch":
                    logger.info("Format %s is skipped in first .pt benchmark run", format_)
                    continue

                model = self._build_YOLObackend(family, size, format_)
                self._warmup(model)
                self._run_model_on_images(model, image_paths, collector)

        return collector.get()

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

            collector.start()
            try:
                model.predict(frame)
            finally:
                collector.stop()


    def _build_YOLObackend(self, family, size, format_) -> YOLOBackend:
        model_path = self._build_model_path(family, size, format_)

        backend = YOLOBackend( # наверное device_type, task_type и т.п. стоит определять при ините BenchmarkRunner
            model=YOLO(model_path, task=TaskType.DETECT.value),
            device=DeviceType.MPS,
            category=Coco,
            task_type=TaskType.DETECT,
            threshold=self.benchmark_config.confidence_threshold or 0.25,
            iou=0.7,
            imgsz=self.benchmark_config.input_size or 640,
            half=False
        )

        return backend

    def _build_model_path(self, family: str, size: str, format_: str) -> str:
        if format_ == "pytorch":
            return f"{family}{size}.pt"
        raise ValueError(f"Unsupported model format for first benchmark run: {format_}")
    
    def _warmup(self, backend: YOLOBackend) -> None:
        # Перед замером нужно прогреть модель, чтобы исключить накладные расходы
        # первого инференса (выделение памяти и тд)

        input_size = self.benchmark_config.input_size or 640
        warmup_iterations = self.benchmark_config.warmup_iterations or 10
        fake_frame = np.zeros((input_size, input_size, 3), dtype=np.uint8)
        for _ in range(warmup_iterations):
            backend.predict(fake_frame) 
        
