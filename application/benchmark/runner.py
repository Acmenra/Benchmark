"""Слой оркестрации бенчмарка."""

from acmenra_cv import YOLOBackend
import acmenra_cv
import cv2
from ultralytics import YOLO

from application.benchmark.metrics.collector import MetricsCollector
from core.entities.config import BenchmarkConfig, BenchmarkRun
from core.entities.metrics import BenchmarkResult
from core.enums.model import Coco, DeviceType, TaskType


class BenchmarkRunner:
    """Координирует загрузку модели, инференс и сбор метрик."""

    def __init__(self, benchmark_config: BenchmarkConfig) -> None:
        self.benchmark_config = benchmark_config
        self.cameras_count = self._count_cameras() # говорили, что есть возможность, но это не ключевое

    def run_suite(self) -> list[BenchmarkResult]:
        results = []

        self._warmup()

        cases = BenchmarkConfig.runs
        for case in cases:
            results.append(self._run_case(case))

        return results
        
    def _run_case(self, case: BenchmarkRun) -> BenchmarkResult:
        if len(case.models) > self.cameras_count:
            raise RuntimeError(
                (f'Моделей для пробега больше, чем камер.'), 
                (f'Моделей: {len(case.models)}, камер: {self.cameras_count}')
            )
        
        models = []
        for model_config in case.models:
            family = model_config.family
            size = model_config.size
            format_ = ... 
            task_type = ...

            model = self._build_YOLObackend(family, size, format_)
            models.append(model)


        collector = MetricsCollector(case)
        

        for model in models:
            ... 
            # пока можно считать, 
            # что модель всегда одна и не использовать это,
            # а реализовать то, что ниже 

        # чекнуть misc\example.py
        cap = cv2.VideoCapture(0)

        while True: 
            collector.start() # по идее должно быть что то по типу такого,
            # collector начинает замер, камера читает кадр, отмечает обьекты
            # collector заканчивает замер,
            # нужно еще подумать сколько по времени это делать
            # Однако тут, проблема в том, как считать температуру, gpu-cpu utillization и power
            # (среднее между одной обработкай или в конце)
   
            ret, frame = cap.read()
            if not ret:
                break
            # sub_frame, tracked_objects = worker.work(frame=frame, is_polygon=True)

            collector.stop()
        # для подсчета фпс 
        # mean_latency_ms = sum(latencies) / len(latencies)
        # fps = 1000.0 / mean_latency_ms 

            
        
        return collector.get()
    
    def _build_YOLObackend(self, family, size, format_) -> YOLOBackend:
        path = family + size + '.' + format_
        model = YOLO(path) # TaskType
        device = DeviceType.AUTO
        task_type = TaskType.E
        
        backend = YOLOBackend(model, device, Coco, task_type)
        model.benchmark

        return backend
    
    def _warmup(self) -> None:
        ...

    def _count_cameras(self) -> int:
        idx = 0

        while True:
            cap = cv2.VideoCapture(idx)
            if not cap.isOpened():
                break
            idx += 1
            cap.release()

        return idx
    