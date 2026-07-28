"""
Адаптер для работы с Apple Silicon (M1/M2/M3/M4) через Metal Performance Shaders.
"""

import platform
import subprocess
import re
import logging

from core.domain.hardware import GPUInfo

logger = logging.getLogger(__name__)


class MPSWorker:
    """
    Самодостаточный адаптер для Apple Silicon.

    Реализует те же методы, что и NVMLWorker и SMIWorker,
    чтобы GPUCollector мог использовать их единообразно.
    """

    def __init__(self) -> None:
        self._is_macos = platform.system() == "Darwin"
        self._chip_name = self._get_chip_name() if self._is_macos else None

    def is_available(self) -> bool:
        """Проверяет, запущен ли код на macOS с Apple Silicon."""
        return self._is_macos and self._chip_name is not None

    def get_info(self) -> GPUInfo:
        """Возвращает статическую информацию о чипе Apple."""
        if not self.is_available():
            return GPUInfo(name=None, memory_mb=None, driver_version=None, cuda_version=None)

        unified_memory_mb = None
        try:
            import psutil
            unified_memory_mb = int(psutil.virtual_memory().total / 1024 / 1024)
        except Exception:
            pass

        return GPUInfo(
            name=self._chip_name,
            memory_mb=unified_memory_mb,
            driver_version=platform.mac_ver()[0],
            cuda_version=None,
        )

    def get_utilization(self) -> float | None:
        """На macOS нет легковесного API для утилизации GPU."""
        return None

    def get_memory_used_mb(self) -> float | None:
        """На macOS VRAM не отслеживается отдельно от системной RAM."""
        return None

    def get_temperature(self) -> float | None:
        """
        Пытается получить температуру SoC.
        Приоритет: сначала быстрый psutil, затем тяжелый powermetrics.
        """
        temp = self._temperature_psutil()
        if temp is not None:
            return temp
        return self._temperature_powermetrics()

    def get_power_watts(self) -> float | None:
        """На macOS нет легковесного API для мощности."""
        return None

    def _get_chip_name(self) -> str | None:
        """Получает название чипа Apple (например, 'Apple M4 Pro')."""
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                check=True, capture_output=True, text=True, timeout=2,
            )
            return result.stdout.strip()
        except Exception as e:
            logger.debug("Не удалось получить имя чипа macOS: %s", e)
            return None

    def _temperature_psutil(self) -> float | None:
        """Быстрый и безопасный способ через psutil."""
        try:
            import psutil
            if not hasattr(psutil, "sensors_temperatures"):
                return None

            temps = psutil.sensors_temperatures()
            for sensor_name, readings in temps.items():
                if "cpu" not in sensor_name.lower() and "gpu" not in sensor_name.lower():
                    continue
                for reading in readings:
                    if 0 <= reading.current < 150:
                        return reading.current
        except (AttributeError, OSError, ImportError) as error:
            logger.debug("psutil не вернул MPS temperature: %s", error)

        return None

    def _temperature_powermetrics(self) -> float | None:
        """
        Тяжелый способ через powermetrics.
        ВНИМАНИЕ: Может занять до 5 секунд и требует sudo.
        """
        try:
            result = subprocess.run(
                ["powermetrics", "-n", "1", "--samplers", "thermal"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return None

            for line in result.stdout.splitlines():
                for pattern in (
                        r"CPU die temperature:\s+([\d.]+)\s+C",
                        r"GPU die temperature:\s+([\d.]+)\s+C",
                        r"SoC.*temperature:\s+([\d.]+)\s+C",
                ):
                    match = re.search(pattern, line)
                    if match:
                        temp = float(match.group(1))
                        if 0 <= temp < 150:
                            return temp
        except (OSError, subprocess.SubprocessError, ValueError, subprocess.TimeoutExpired) as error:
            logger.debug("powermetrics не вернул MPS temperature: %s", error)

        return None