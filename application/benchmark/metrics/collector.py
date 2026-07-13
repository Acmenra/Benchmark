# application\benchmark\metrics\collector.py


from core.entities.config import BenchmarkRun
from core.entities.metrics import BenchmarkResult


class MetricsCollector:
    def __init__(self, benchmark_run: BenchmarkRun) -> None:
        # Возможно потом нужно будет собирать только определенные метрики 
        # при помощи MetricsConfig
        self.benchmark_run = benchmark_run
        history = []

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def get(self) -> BenchmarkResult:
        ...

        return BenchmarkResult(
            self.benchmark_run,
            None,
            None,
            None
        )