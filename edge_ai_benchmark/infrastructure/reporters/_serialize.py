"""Общая сериализация `BenchmarkResult` в плоский словарь для всех reporters."""

from __future__ import annotations

from typing import Any

from edge_ai_benchmark.core.entities import BenchmarkResult


def result_to_flat_dict(result: BenchmarkResult) -> dict[str, Any]:
    """Свести `BenchmarkResult` к плоскому словарю метрик для отчётов.

    Args:
        result: Результат одной комбинации модель×формат.

    Returns:
        Плоский словарь с ключами модели/формата, производительности,
        ресурсов, энергопотребления и точности (см. пример JSON в README).
    """
    flat: dict[str, Any] = {
        "model": result.model,
        "format": result.format.value,
        "task": result.task,
        "fps": round(result.performance.fps, 2),
        "latency_p50_ms": round(result.performance.end_to_end_latency.p50_ms, 2),
        "latency_p95_ms": round(result.performance.end_to_end_latency.p95_ms, 2),
        "latency_p99_ms": round(result.performance.end_to_end_latency.p99_ms, 2),
        "compute_latency_p50_ms": round(result.performance.compute_latency.p50_ms, 2),
        "compute_latency_p95_ms": round(result.performance.compute_latency.p95_ms, 2),
        "compute_latency_p99_ms": round(result.performance.compute_latency.p99_ms, 2),
        "gpu_utilization_pct": _round_or_none(result.hardware.gpu_utilization_pct),
        "vram_usage_peak_mb": _round_or_none(result.hardware.vram_usage_peak_mb),
        "cpu_percent": _round_or_none(result.hardware.cpu_percent),
        "ram_used_mb": _round_or_none(result.hardware.ram_used_mb),
        "disk_read_mb": _round_or_none(result.hardware.disk_read_mb),
        "disk_write_mb": _round_or_none(result.hardware.disk_write_mb),
        "power_w": _round_or_none(result.power.power_w),
        "fps_per_watt": _round_or_none(result.fps_per_watt),
        "gpu_temperature_c": _round_or_none(result.power.gpu_temperature_c),
        "cpu_temperature_c": _round_or_none(result.power.cpu_temperature_c),
    }
    if result.accuracy is not None:
        flat.update(
            {
                "precision": _round_or_none(result.accuracy.precision),
                "recall": _round_or_none(result.accuracy.recall),
                "map50": _round_or_none(result.accuracy.map50),
                "map50_95": _round_or_none(result.accuracy.map50_95),
                "mask_map50": _round_or_none(result.accuracy.mask_map50),
                "mask_map50_95": _round_or_none(result.accuracy.mask_map50_95),
            }
        )
    return flat


def _round_or_none(value: float | None, ndigits: int = 2) -> float | None:
    return round(value, ndigits) if value is not None else None
