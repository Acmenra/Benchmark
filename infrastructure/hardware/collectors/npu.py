# infrastructure/hardware/collectors/npu.py

import logging
import platform
from pathlib import Path

from infrastructure.hardware.collectors.base import is_valid_temperature

logger = logging.getLogger(__name__)


class NPUCollector:
    """Сборщик температурных метрик NPU (Hailo, Apple Neural Engine и др.)."""

    def is_temperature_sensor_available(self) -> bool:
        """Определяет доступность температурных датчиков NPU."""
        return self.tmp() is not None

    def tmp(self) -> float | None:
        """Возвращает текущую температуру NPU в °C."""
        if platform.system() != "Linux":
            return None

        temperature = self._temperature_hwmon()
        if temperature is not None:
            return temperature

        return self._temperature_hailo_sysfs()

    def _temperature_hwmon(self) -> float | None:
        """Поиск NPU-датчиков в /sys/class/hwmon."""
        hwmon_root = Path("/sys/class/hwmon")
        if not hwmon_root.exists():
            return None

        npu_driver_names = (
            "hailo",
            "npu",
            "neural",
        )

        for hwmon_dir in hwmon_root.iterdir():
            try:
                name_file = hwmon_dir / "name"
                if not name_file.exists():
                    continue

                driver_name = name_file.read_text(encoding="utf-8", errors="ignore").strip().lower()
                if not any(token in driver_name for token in npu_driver_names):
                    continue

                for temp_input in sorted(hwmon_dir.glob("temp*_input")):
                    try:
                        raw_value = temp_input.read_text(encoding="utf-8", errors="ignore").strip()
                        temp = float(raw_value) / 1000.0
                        if is_valid_temperature(temp):
                            return temp
                    except (OSError, ValueError):
                        continue
            except OSError:
                continue

        return None

    def _temperature_hailo_sysfs(self) -> float | None:
        """Получение температуры Hailo NPU через sysfs."""
        hailo_paths = (
            Path("/sys/class/hailo/hailo0/device/temperature"),
            Path("/sys/class/hailo_chardev/hailo0/temperature"),
        )

        for path in hailo_paths:
            if not path.exists():
                continue
            try:
                temp = float(path.read_text(encoding="utf-8", errors="ignore").strip())
                if is_valid_temperature(temp):
                    return temp
            except (OSError, ValueError):
                continue

        return None
