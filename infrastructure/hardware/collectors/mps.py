# infrastructure/hardware/collectors/mps.py

import logging
import platform
import re
import subprocess

from infrastructure.hardware.collectors.temperature import _is_valid_temperature

logger = logging.getLogger(__name__)


class MPSCollector:
    """Сборщик температурных метрик Apple MPS/SoC."""

    def is_temperature_sensor_available(self) -> bool:
        """Определяет доступность температурных датчиков MPS."""
        if platform.system() != "Darwin":
            return False
        return self.tmp() is not None

    def tmp(self) -> float | None:
        """Возвращает текущую температуру GPU/SoC для Apple MPS в градусах Цельсия."""
        if platform.system() != "Darwin":
            return None

        temperature = self._temperature_powermetrics()
        if temperature is not None:
            return temperature

        return self._temperature_psutil()

    def _temperature_powermetrics(self) -> float | None:
        """Получить температуру через powermetrics на macOS."""
        try:
            result = subprocess.run(
                ["powermetrics", "-n", "1", "--samplers", "thermal"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                logger.debug("powermetrics не вернул MPS temperature: %s", result.stderr)
                return None

            for line in result.stdout.splitlines():
                for pattern in (
                    r"CPU die temperature:\s+([\d.]+)\s+C",
                    r"GPU die temperature:\s+([\d.]+)\s+C",
                    r"CPU.*temperature:\s+([\d.]+)\s+C",
                    r"GPU.*temperature:\s+([\d.]+)\s+C",
                    r"SoC.*temperature:\s+([\d.]+)\s+C",
                ):
                    match = re.search(pattern, line)
                    if match is None:
                        continue

                    temp = float(match.group(1))
                    if _is_valid_temperature(temp):
                        return temp
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            logger.debug("powermetrics не вернул MPS temperature: %s", error)

        return None

    def _temperature_psutil(self) -> float | None:
        """Fallback: получить температуру через psutil, если датчики доступны."""
        try:
            import psutil

            if not hasattr(psutil, "sensors_temperatures"):
                return None

            temps = psutil.sensors_temperatures()
            for sensor_name, readings in temps.items():
                if "cpu" not in sensor_name.lower() and "gpu" not in sensor_name.lower():
                    continue
                for reading in readings:
                    if _is_valid_temperature(reading.current):
                        return reading.current
        except (AttributeError, OSError, ImportError) as error:
            logger.debug("psutil не вернул MPS temperature: %s", error)

        return None
