# infrastructure/hardware/collectors/collector.py

import logging
import platform
import subprocess

from core.domain.hardware.ram_info import RAMInfo
from core.domain.config.system import SystemInfoConfig
from infrastructure.hardware.collectors.base import BaseHardwareCollector


logger = logging.getLogger(__name__)


class RAMCollector(BaseHardwareCollector):
    """Сборщик статической информации об оперативной памяти (RAM)."""

    def __init__(self, system_info_config: SystemInfoConfig | None = None) -> None:
        super().__init__(system_info_config)
        self._hardware_info = self._gather_static_info()

    def get_hardware_info(self) -> RAMInfo:
        """Возвращает кэшированную статическую информацию о RAM."""
        return self._hardware_info

    def _gather_static_info(self) -> RAMInfo:
        total_mb = None
        ram_type = None

        try:
            import psutil
            mem = psutil.virtual_memory()
            total_mb = int(mem.total / (1024 ** 2))
        except ImportError:
            logger.warning("Модуль psutil не установлен, объем RAM определить не удалось.")

        ram_type = self._get_ram_type()

        return RAMInfo(
            total_mb=total_mb,
            type=ram_type,
            speed_mhz=None
        )

    def _get_ram_type(self) -> str | None:
        """Пытается определить тип памяти в зависимости от ОС."""
        system = platform.system()

        if system == "Darwin":
            return "Unified Memory"

        elif system == "Linux":
            try:
                model = subprocess.run(
                    ["cat", "/proc/device-tree/model"],
                    capture_output=True, text=True, timeout=2
                ).stdout.strip().lower()

                if "raspberry" in model:
                    return "LPDDR"
                elif "jetson" in model or "orin" in model:
                    return "LPDDR"
            except Exception:
                pass

        return None

    def get_metrics(self) -> None:
        """
        RAM Collector отвечает только за статику в этом контексте.
        Динамические метрики (usage) собираются отдельно, если нужно.
        """
        return None