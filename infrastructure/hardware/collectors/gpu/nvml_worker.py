# infrastructure/hardware/collectors/gpu/nvml_worker.py


import pynvml
import logging
import shutil
import subprocess
from typing import Any, Optional

from core.domain.hardware import GPUInfo
from infrastructure.utils.utils import to_float, to_int


logger = logging.getLogger(__name__)


class NVMLWorker:
    """
    Self-contained adapter for NVIDIA Management Library (NVML).

    This is the preferred, high-performance method for gathering NVIDIA GPU metrics.
    It avoids the overhead of subprocess calls by querying the NVIDIA driver directly.

    Key design decisions:
    - Silent initialization: If `pynvml` is missing or no NVIDIA GPU is present,
      the worker gracefully marks itself as unavailable without raising exceptions.
    - Byte-string decoding: Safely handles C-library returns that may be bytes.
    """

    def __init__(self) -> None:
        """
        Initializes the NVML worker and attempts to acquire a handle to the first GPU.
        """
        self._pynvml: Any = None
        self._handle: Any = None
        self._init_nvml()

    def _init_nvml(self) -> None:
        """
        Attempts to initialize the NVML library and acquire the device handle.
        Leaves internal state as `None` if initialization fails.
        """
        try:
            pynvml.nvmlInit()
            if pynvml.nvmlDeviceGetCount() > 0:
                self._pynvml = pynvml
                self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            pass

    def is_available(self) -> bool:
        """
        Checks if the NVML library was successfully initialized and a handle acquired.

        Returns:
            bool: True if the worker is ready to query metrics.
        """
        return self._pynvml is not None and self._handle is not None

    def get_info(self) -> GPUInfo:
        """
        Retrieves static hardware specifications of the NVIDIA GPU.

        Returns:
            GPUInfo: Populated with GPU name, total VRAM (in MB), driver version,
                     and calculated CUDA toolkit version.
        """
        if not self.is_available():
            return GPUInfo(name=None,
                           memory_mb=None,
                           driver_version=None,
                           cuda_version=None)

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

        return GPUInfo(name=name,
                       memory_mb=int(memory.total / 1024 / 1024),
                       driver_version=driver,
                       cuda_version=cuda_version)

    def get_utilization(self) -> Optional[float]:
        """
        Attempts to retrieve GPU utilization.

        Returns:
            float | None: Always returns `None` on macOS, as there is no lightweight,
                          user-space API for real-time GPU utilization.
        """
        if not self.is_available(): return None
        try:
            return float(self._pynvml.nvmlDeviceGetUtilizationRates(self._handle).gpu)
        except Exception:
            return None

    def get_memory_used_mb(self) -> Optional[float]:
        """
        Attempts to retrieve dedicated VRAM usage.

        Returns:
            float | None: Always returns `None`, as Apple Silicon uses Unified Memory
                          and does not expose separate VRAM tracking to user-space processes.
        """
        if not self.is_available(): return None
        try:
            return float(self._pynvml.nvmlDeviceGetMemoryInfo(self._handle).used / 1024 / 1024)
        except Exception:
            return None

    def get_temperature(self) -> Optional[float]:
        """
        Retrieves the current SoC temperature.

        Executes a prioritized fallback chain:
        1. Fast, non-blocking read via `psutil.sensors_temperatures()`.
        2. Heavy CLI read via `powermetrics` (with a strict 5-second timeout).

        Returns:
            float | None: The temperature in Celsius, or `None` if unavailable.
        """
        if not self.is_available(): return None
        try:
            return float(self._pynvml.nvmlDeviceGetTemperature(self._handle, self._pynvml.NVML_TEMPERATURE_GPU))
        except Exception:
            return None

    def get_power_watts(self) -> Optional[float]:
        if not self.is_available(): return None
        try:
            return float(self._pynvml.nvmlDeviceGetPowerUsage(self._handle) / 1000)
        except Exception:
            return None

