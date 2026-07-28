# infrastructure/hardware/collectors/gpu/nvml_worker.py

import shutil
import subprocess
import logging
from typing import Any

from core.domain.hardware import GPUInfo
from infrastructure.utils.utils import to_float, to_int


logger = logging.getLogger(__name__)


class NVMLWorker:
    """Самодостаточный адаптер для работы с NVIDIA Management Library."""

    def __init__(self) -> None:
        self._pynvml: Any = None
        self._handle: Any = None
        self._init_nvml()

    def _init_nvml(self) -> None:
        try:
            import pynvml
            pynvml.nvmlInit()
            if pynvml.nvmlDeviceGetCount() > 0:
                self._pynvml = pynvml
                self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            # pynvml не установлен или нет GPU NVIDIA
            pass

    def is_available(self) -> bool:
        return self._pynvml is not None and self._handle is not None

    def get_info(self) -> GPUInfo:
        if not self.is_available():
            return GPUInfo(name=None, memory_mb=None, driver_version=None, cuda_version=None)

        name = self._pynvml.nvmlDeviceGetName(self._handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8", errors="ignore")

        memory = self._pynvml.nvmlDeviceGetMemoryInfo(self._handle)
        driver = self._pynvml.nvmlSystemGetDriverVersion()
        if isinstance(driver, bytes):
            driver = driver.decode("utf-8", errors="ignore")

        cuda_version = None
        try:
            ver = self._pynvml.nvmlSystemGetCudaDriverVersion()
            cuda_version = f"{ver // 1000}.{(ver % 1000) // 10}"
        except Exception:
            pass

        return GPUInfo(
            name=name,
            memory_mb=int(memory.total / 1024 / 1024),
            driver_version=driver,
            cuda_version=cuda_version,
        )

    def get_utilization(self) -> float | None:
        if not self.is_available(): return None
        try:
            return float(self._pynvml.nvmlDeviceGetUtilizationRates(self._handle).gpu)
        except Exception:
            return None

    def get_memory_used_mb(self) -> float | None:
        if not self.is_available(): return None
        try:
            return float(self._pynvml.nvmlDeviceGetMemoryInfo(self._handle).used / 1024 / 1024)
        except Exception:
            return None

    def get_temperature(self) -> float | None:
        if not self.is_available(): return None
        try:
            return float(self._pynvml.nvmlDeviceGetTemperature(self._handle, self._pynvml.NVML_TEMPERATURE_GPU))
        except Exception:
            return None

    def get_power_watts(self) -> float | None:
        if not self.is_available(): return None
        try:
            return float(self._pynvml.nvmlDeviceGetPowerUsage(self._handle) / 1000)
        except Exception:
            return None

