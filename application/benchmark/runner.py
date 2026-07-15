# application/benchmark/runner.py

import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

"""Слой оркестрации бенчмарка."""


import cv2
from acmenra_cv import YOLOBackend
from ultralytics import YOLO

from application.benchmark.metrics.collector import MetricsCollector
from core.entities.config import BenchmarkConfig, BenchmarkRun
from core.entities.metrics import BenchmarkResult
from core.enums.model import Coco, DeviceType, TaskType


class BenchmarkRunner:
    """Координирует загрузку модели, инференс и сбор метрик."""

    def __init__(self, benchmark_config: BenchmarkConfig) -> None:
        self.benchmark_config = benchmark_config

    def run_suite(self) -> list[BenchmarkResult]:
        results = []

        cases = BenchmarkConfig.runs
        for case in cases:
            results.append(self._run_case(case))

        return results
        
    def _run_case(self, case: BenchmarkRun) -> BenchmarkResult:
        dataset_path = "/path/to/your/images"  # временно здесь, по хорошему надо с конфига брать
        models = []
        for model_config in case.models:
            family = model_config.family
            size = model_config.size
            format_ = ...

            model = self._build_YOLObackend(family, size, format_)
            models.append(model)

            self._warmup(model) # прогрев модели


        for model in models:
            ... 
            # пока можно считать, 
            # что модель всегда одна и не использовать это,
            # а реализовать то, что ниже 

        # Проверяем, что папка существует
        if not os.path.isdir(dataset_path):
            raise ValueError(f"Dataset path not found: {dataset_path}")

        # Собираем все картинки
        import glob
        extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        image_paths = []
        for ext in extensions:
            image_paths.extend(glob.glob(os.path.join(dataset_path, f'*{ext}')))
            image_paths.extend(glob.glob(os.path.join(dataset_path, f'*{ext.upper()}')))
        if not image_paths:
            raise ValueError(f"No images found in {dataset_path}")
        image_paths.sort()  # для воспроизводимости тестов подаем данные всегда в одном порядке

        # Инициализируем коллектор
        collector = MetricsCollector(case)

        # Цикл по каждому изображению
        for img_path in image_paths:
            frame = cv2.imread(img_path)
            if frame is None:
                logger.warning(f"Could not read {img_path}, skipping")
                continue

            collector.start()  # начать замер для этого кадра

            # Здесь сам инференс:
            # result = model.predict(frame)
            # или sub_frame, tracked_objects = worker.work(frame=frame, is_polygon=True)

            collector.stop()  # закончить замер

        # После обработки всех изображений собираем статистику
        return collector.get()


    def _build_YOLObackend(self, family, size, format_) -> YOLOBackend:
        model_path = f"{family}{size}.{format_}"

        backend = YOLOBackend( # наверное device_type, task_type и т.п. стоит определять при ините BenchmarkRunner
            model=YOLO(model_path, task=TaskType.SEGMENT.value),
            device=DeviceType.AUTO,
            category=Coco,
            task_type=TaskType.SEGMENT,
            threshold=0.60,
            iou=0.7,
            imgsz=1280,
            half=False
        )

        return backend
    
    def _warmup(self, backend: YOLOBackend) -> None:
        # Перед замером нужно прогреть модель, чтобы исключить накладные расходы
        # первого инференса (выделение памяти и тд)

        fake_frame = np.zeros((640, 640, 3), dtype=np.uint8)
        for _ in range(10): # итераций прогрева
            backend.predict(fake_frame) 
            # можно еще не создавать кадры, а брать первые из cap = cv2.VideoCapture(0)
        
