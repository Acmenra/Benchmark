"""Чистые вычисления производительности: FPS и перцентили задержки.

Ничего не знает про модели, железо или файлы — только математика над списками
чисел (мс), возвращаемая как сущности `core.entities`.
"""

from __future__ import annotations

import numpy as np

from edge_ai_benchmark.core.entities import LatencyStats, PerformanceResult


def compute_percentiles(latencies_ms: list[float]) -> LatencyStats:
    """Посчитать перцентили p50/p95/p99 списка задержек.

    Args:
        latencies_ms: Список задержек в миллисекундах (непустой).

    Returns:
        `LatencyStats` с p50/p95/p99 в миллисекундах.

    Raises:
        ValueError: Если `latencies_ms` пуст.
    """
    if not latencies_ms:
        raise ValueError("latencies_ms не должен быть пустым")
    arr = np.asarray(latencies_ms, dtype=np.float64)
    return LatencyStats(
        p50_ms=float(np.percentile(arr, 50)),
        p95_ms=float(np.percentile(arr, 95)),
        p99_ms=float(np.percentile(arr, 99)),
    )


def compute_fps(latencies_ms: list[float]) -> float:
    """Посчитать FPS по среднему значению задержек.

    Args:
        latencies_ms: Список задержек в миллисекундах (непустой).

    Returns:
        Кадров в секунду (`1000 / mean(latencies_ms)`).

    Raises:
        ValueError: Если `latencies_ms` пуст или среднее значение равно нулю.
    """
    if not latencies_ms:
        raise ValueError("latencies_ms не должен быть пустым")
    mean_ms = float(np.mean(latencies_ms))
    if mean_ms <= 0:
        raise ValueError("Среднее значение задержки должно быть положительным")
    return 1000.0 / mean_ms


def build_performance_result(
    compute_latencies_ms: list[float],
    end_to_end_latencies_ms: list[float],
) -> PerformanceResult:
    """Собрать `PerformanceResult` из двух наборов сырых замеров задержки.

    Args:
        compute_latencies_ms: Задержки "чистого" forward pass модели (без
            учёта передачи данных RAM -> устройство), мс.
        end_to_end_latencies_ms: Полные задержки одного кадра — препроцессинг,
            H2D-передача, forward pass, постпроцессинг — то, что видит
            потребитель в realtime-стриминге, мс.

    Returns:
        `PerformanceResult` с fps (посчитанным по end-to-end) и обеими
        перцентильными раскладками задержки.
    """
    return PerformanceResult(
        fps=compute_fps(end_to_end_latencies_ms),
        compute_latency=compute_percentiles(compute_latencies_ms),
        end_to_end_latency=compute_percentiles(end_to_end_latencies_ms),
    )
