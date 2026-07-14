# application/benchmark/metrics/collector.py

from core.entities.config import BenchmarkRun
from core.entities.metrics import BenchmarkResult, PerformanceMetrics


class MetricsCollector: # TODO собирает ВСЮ информацию за 1 запуск модели (конкретная модель, конкретный формат, конкретные параметры)
    def __init__(self, benchmark_run: BenchmarkRun) -> None:
        # Возможно потом нужно будет собирать только определенные метрики 
        # при помощи MetricsConfig
        self.benchmark_run = benchmark_run
        
        self.performance = PerformanceMetrics()
        self.hardware = HardwareMetrics()
        self.power = PowerMetrics()

    def start(self) -> None:
        self.time = ... # текущее точное время

    def stop(self) -> None:
        delta = ... # self.time - current time время для latency

    def get(self) -> BenchmarkResult: # TODO отдает метрики "какие" (перечислить, прям по классово), лежит в application/benchmark/metrics
        ...

        return BenchmarkResult(
            self.benchmark_run,
            None,
            None,
            None
        )
