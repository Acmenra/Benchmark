"""
Самодостаточный адаптер для работы с NPU (в первую очередь Hailo-8/8L).
"""

import logging
import platform
from pathlib import Path

from core.domain.hardware import NPUInfo


logger = logging.getLogger(__name__)


class HailoWorker:
    """Адаптер для получения метрик и информации о Hailo NPU."""

    def __init__(self) -> None:
        self._is_linux = platform.system() == "Linux"
        self._is_available = self._check_availability() if self._is_linux else False

    def _check_availability(self) -> bool:
        """Быстрая проверка наличия путей Hailo в системе."""
        return (
                Path("/sys/class/hailo/hailo0/device/temperature").exists() or
                Path("/sys/class/hailo_chardev/hailo0/temperature").exists() or
                self._find_hwmon_temp() is not None
        )

    def is_available(self) -> bool:
        return self._is_linux and self._is_available

    def get_info(self) -> NPUInfo:
        """Возвращает статическую информацию о NPU."""
        if not self.is_available():
            return NPUInfo(name=None, architecture=None)

        import platform as plt
        return NPUInfo(
            name="Hailo-8 / Hailo-8L",
            architecture=plt.machine(),
        )

    def get_temperature(self) -> float | None:
        """Получает температуру NPU. Приоритет: прямой sysfs, затем hwmon."""
        if not self.is_available():
            return None

        temp = self._temperature_hailo_sysfs()
        if temp is not None:
            return temp

        return self._find_hwmon_temp()

    def _find_hwmon_temp(self) -> float | None:
        """Найти NPU-датчики в /sys/class/hwmon."""
        hwmon_root = Path("/sys/class/hwmon")
        if not hwmon_root.exists():
            return None

        npu_driver_names = ("hailo", "npu", "neural")

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
                        if 0 <= temp < 150:
                            return temp
                    except (OSError, ValueError):
                        continue
            except OSError:
                continue
        return None

    def _temperature_hailo_sysfs(self) -> float | None:
        """Получить температуру Hailo NPU через прямой sysfs."""
        hailo_paths = (
            Path("/sys/class/hailo/hailo0/device/temperature"),
            Path("/sys/class/hailo_chardev/hailo0/temperature"),
        )

        for path in hailo_paths:
            if path.exists():
                try:
                    temp = float(path.read_text(encoding="utf-8", errors="ignore").strip())
                    if 0 <= temp < 150:
                        return temp
                except (OSError, ValueError) as error:
                    logger.debug("Hailo sysfs %s не вернул температуру: %s", path, error)
                    continue
        return None

    def get_utilization(self) -> float | None:
        return None

    def get_power_watts(self) -> float | None:
        return None