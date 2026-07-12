"""Слой оркестрации бенчмарка."""

from core.entities.metrics import BenchmarkResult


class BenchmarkRunner:
    """Координирует загрузку модели, инференс и сбор метрик."""

    # потом будет benchmark_config: 'BenchmarkConfig'
    def __init__(self, benchmark_config: ...) -> None:
        self.benchmark_config = benchmark_config

    def run_suite(self) -> list[BenchmarkResult]:
        # выполнить все прогоны.

        cases = [] #cases = benchmark_config.runs
        for case in cases:
            self.run_case(...)

        raise NotImplementedError()
    
    def run_case(self, case: ...,) -> BenchmarkResult:
        # Выполнить один прогон
        raise NotImplementedError()
