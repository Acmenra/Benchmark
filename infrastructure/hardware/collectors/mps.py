# infrastructure/hardware/collectors/mps.py

import logging
import platform
import re
import subprocess

from infrastructure.hardware.collectors.base import is_valid_temperature

logger = logging.getLogger(__name__)


class MPSCollector:
    """Сборщик температурных метрик Apple MPS (Metal Performance Shaders)."""

    def is_temperature_sensor_available(self) -> bool:
        """Определяет доступность температурных датчиков MPS."""
        if platform.system() != "Darwin":
            return False
        return self.tmp() is not None

    def tmp(self) -> float | None:
        """Возвращает текущую температуру GPU/SoC для Apple MPS в °C."""
        if platform.system() != "Darwin":
            return None

        temperature = self._temperature_powermetrics()
        if temperature is not None:
            return temperature

        return self._temperature_psutil()

    def _temperature_powermetrics(self) -> float | None:
        """Получение температуры через powermetrics на macOS."""
        try:
            result = subprocess.run(
                ["powermetrics", "-n", "1", "--samplers", "smc"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None

            for line in result.stdout.splitlines():
                match = re.search(r"GPU die temperature:\s+([\d.]+)\s+C", line)
                if match:
                    temp = float(match.group(1))
                    if is_valid_temperature(temp):
                        return temp

                match = re.search(r"CPU die temperature:\s+([\d.]+)\s+C", line)
                if match:
                    temp = float(match.group(1))
                    if is_valid_temperature(temp):
                        return temp
        except (OSError, subprocess.SubprocessError, ValueError):
            pass

        return None

    def _temperature_psutil(self) -> float | None:
        """Fallback: получение температуры через psutil на macOS."""
        try:
            import psutil

            if not hasattr(psutil, "sensors_temperatures"):
                return None

            temps = psutil.sensors_temperatures()
            for sensor_name, readings in temps.items():
                if "gpu" not in sensor_name.lower():
                    continue
                for reading in readings:
                    if is_valid_temperature(reading.current):
                        return reading.current
        except (AttributeError, OSError, ImportError):
            pass

        return None
