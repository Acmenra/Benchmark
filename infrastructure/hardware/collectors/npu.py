# infrastructure/hardware/collectors/npu.py

import logging
import platform
from pathlib import Path

from infrastructure.hardware.collectors.temperature import _is_valid_temperature


logger = logging.getLogger(__name__)


class NPUCollector:
    """Сборщик температурных метрик NPU, например Hailo."""

    def is_temperature_sensor_available(self) -> bool:
        """Определяет доступность температурных датчиков NPU."""
        return self.tmp() is not None

    def tmp(self) -> float | None:
        """Возвращает текущую температуру NPU в градусах Цельсия."""
        if platform.system() != "Linux":
            return None

        temperature = self._temperature_hwmon()
        if temperature is not None:
            return temperature

        return self._temperature_hailo_sysfs()

    def _temperature_hwmon(self) -> float | None:
        """Найти NPU-датчики в /sys/class/hwmon."""
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

                driver_name = name_file.read_text(
                    encoding="utf-8",
                    errors="ignore",
                ).strip().lower()
                if not any(token in driver_name for token in npu_driver_names):
                    continue

                for temp_input in sorted(hwmon_dir.glob("temp*_input")):
                    try:
                        raw_value = temp_input.read_text(
                            encoding="utf-8",
                            errors="ignore",
                        ).strip()
                        temp = float(raw_value) / 1000.0
                        if _is_valid_temperature(temp):
                            return temp
                    except (OSError, ValueError) as error:
                        logger.debug("hwmon %s не вернул NPU temperature: %s", temp_input, error)
                        continue
            except OSError as error:
                logger.debug("hwmon %s не удалось проверить как NPU sensor: %s", hwmon_dir, error)
                continue

        return None

    def _temperature_hailo_sysfs(self) -> float | None:
        """Получить температуру Hailo NPU через sysfs."""
        hailo_paths = (
            Path("/sys/class/hailo/hailo0/device/temperature"),
            Path("/sys/class/hailo_chardev/hailo0/temperature"),
        )

        for path in hailo_paths:
            if not path.exists():
                continue
            try:
                temp = float(path.read_text(encoding="utf-8", errors="ignore").strip())
                if _is_valid_temperature(temp):
                    return temp
            except (OSError, ValueError) as error:
                logger.debug("Hailo sysfs %s не вернул NPU temperature: %s", path, error)
                continue

        return None
