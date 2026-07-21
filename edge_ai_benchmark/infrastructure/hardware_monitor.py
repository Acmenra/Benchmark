"""Мониторинг ресурсов (CPU/RAM/disk I/O/GPU/питание/температура) во время бенчмарка."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

import psutil

from edge_ai_benchmark.core.entities import HardwareUsageResult

logger = logging.getLogger(__name__)

try:
    import pynvml as _pynvml
except ImportError:
    _pynvml = None


@dataclass
class ResourceSnapshot:
    """Средние значения ресурсов, накопленные с момента `ResourceMonitor.start()`."""

    cpu_percent: float | None
    gpu_utilization_pct: float | None
    ram_used_mb: float | None
    power_w: float | None
    gpu_temperature_c: float | None


class ResourceMonitor:
    """Фоновый сэмплер загрузки CPU/RAM/disk/GPU/питания/температуры процесса-бенчмарка.

    Использование:
        monitor = ResourceMonitor()
        monitor.start()
        ... прогон бенчмарка ...
        result = monitor.stop()
    """

    def __init__(self, sample_interval_s: float = 0.2) -> None:
        self._sample_interval_s = sample_interval_s
        self._process = psutil.Process()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._cpu_samples: list[float] = []
        self._cpu_per_core_samples: list[list[float]] = []
        self._ram_samples: list[float] = []
        self._gpu_util_samples: list[float] = []
        self._power_samples: list[float] = []
        self._gpu_temp_samples: list[float] = []
        self._vram_peak_mb: float | None = None
        self._disk_start = None
        self._nvml_handle: Any = None

    def start(self) -> None:
        """Запустить фоновый поток сэмплирования метрик."""
        self._cpu_samples.clear()
        self._cpu_per_core_samples.clear()
        self._ram_samples.clear()
        self._gpu_util_samples.clear()
        self._power_samples.clear()
        self._gpu_temp_samples.clear()
        self._vram_peak_mb = None
        self._stop_event.clear()
        try:
            self._disk_start = self._process.io_counters()
        except (psutil.AccessDenied, AttributeError):
            self._disk_start = None

        # nvmlInit/nvmlDeviceGetHandleByIndex один раз за прогон, а не на
        # каждый сэмпл — избегаем повторной инициализации NVML каждые
        # `sample_interval_s`, особенно заметно на длинных duration_minutes-прогонах.
        self._nvml_handle = None
        if _pynvml is not None:
            try:
                _pynvml.nvmlInit()
                self._nvml_handle = _pynvml.nvmlDeviceGetHandleByIndex(0)
            except Exception:
                logger.debug(
                    "Инициализация NVML не удалась — GPU-метрики недоступны", exc_info=True
                )

        self._process.cpu_percent(interval=None)  # прогрев счётчика psutil
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def _sample_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._cpu_samples.append(self._process.cpu_percent(interval=None))
                self._cpu_per_core_samples.append(list(psutil.cpu_percent(percpu=True)))
                self._ram_samples.append(self._process.memory_info().rss / (1024**2))
            except psutil.NoSuchProcess:
                break

            if self._nvml_handle is not None:
                try:
                    util = _pynvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
                    mem = _pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
                    self._gpu_util_samples.append(float(util.gpu))
                    vram_mb = mem.used / (1024**2)
                    self._vram_peak_mb = max(self._vram_peak_mb or 0.0, vram_mb)
                except Exception:
                    logger.debug("Сэмпл загрузки/VRAM GPU не удался", exc_info=True)
                try:
                    self._power_samples.append(
                        _pynvml.nvmlDeviceGetPowerUsage(self._nvml_handle) / 1000.0
                    )
                except Exception:
                    logger.debug("Сэмпл мощности GPU не удался", exc_info=True)
                try:
                    self._gpu_temp_samples.append(
                        float(
                            _pynvml.nvmlDeviceGetTemperature(
                                self._nvml_handle, _pynvml.NVML_TEMPERATURE_GPU
                            )
                        )
                    )
                except Exception:
                    logger.debug("Сэмпл температуры GPU не удался", exc_info=True)

            time.sleep(self._sample_interval_s)

    def snapshot(self) -> ResourceSnapshot:
        """Снимок средних значений по сэмплам, накопленным с момента `start()`.

        В отличие от `stop()`, не останавливает сэмплирование — используется
        для периодического прогресс-лога во время долгого прогона.

        Returns:
            `ResourceSnapshot` со средними по накопленным сэмплам (`None` для
            метрик, недоступных на этой платформе/без GPU).
        """
        return ResourceSnapshot(
            cpu_percent=_mean_or_none(self._cpu_samples),
            gpu_utilization_pct=_mean_or_none(self._gpu_util_samples),
            ram_used_mb=_mean_or_none(self._ram_samples),
            power_w=_mean_or_none(self._power_samples),
            gpu_temperature_c=_mean_or_none(self._gpu_temp_samples),
        )

    def stop(self) -> HardwareUsageResult:
        """Остановить сэмплирование и вернуть агрегированный результат.

        Returns:
            `HardwareUsageResult` со средними/пиковыми значениями за период
            между `start()` и `stop()`.
        """
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._sample_interval_s * 5)

        if self._nvml_handle is not None:
            try:
                _pynvml.nvmlShutdown()
            except Exception:
                logger.debug("Завершение NVML не удалось", exc_info=True)
            self._nvml_handle = None

        disk_read_mb = None
        disk_write_mb = None
        if self._disk_start is not None:
            try:
                disk_end = self._process.io_counters()
                disk_read_mb = (disk_end.read_bytes - self._disk_start.read_bytes) / (1024**2)
                disk_write_mb = (disk_end.write_bytes - self._disk_start.write_bytes) / (1024**2)
            except (psutil.AccessDenied, AttributeError, psutil.NoSuchProcess):
                logger.debug("Метрики disk I/O недоступны на этой платформе", exc_info=True)

        return HardwareUsageResult(
            cpu_percent=_mean_or_none(self._cpu_samples),
            cpu_percent_per_core=_mean_per_core(self._cpu_per_core_samples),
            ram_used_mb=_mean_or_none(self._ram_samples),
            disk_read_mb=disk_read_mb,
            disk_write_mb=disk_write_mb,
            gpu_utilization_pct=_mean_or_none(self._gpu_util_samples),
            vram_usage_peak_mb=self._vram_peak_mb,
        )


def _mean_or_none(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _mean_per_core(samples: list[list[float]]) -> list[float]:
    if not samples:
        return []
    n_cores = len(samples[0])
    return [sum(sample[i] for sample in samples) / len(samples) for i in range(n_cores)]
