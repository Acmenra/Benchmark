# infrastructure/hardware/collectors/gpu.py

import time
import shutil
import logging
import subprocess
from typing import Any
from pathlib import Path
import platform as platform_module

from core.domain.hardware import GPUInfo
from core.domain.hardware.enums import PlatformType
from core.domain.config.system import SystemInfoConfig
from core.domain.metrics import MetricStatistics, GPUMetrics, DataPoint
from infrastructure.hardware.collectors.base import BaseCollector
from infrastructure.utils.utils import to_float, to_int, read_text

logger = logging.getLogger(__name__)


class GPUCollector(BaseCollector):
    """Сборщик статической информации и runtime-метрик GPU."""

    def __init__(self, system_info_config: SystemInfoConfig | None = None) -> None:
        super().__init__(
            system_info_config
            or SystemInfoConfig(
                collect_сpu=True,
                collect_gpu=True,
                collect_power=False,
                collect_temperature=False,
            )
        )
        self._pynvml: Any | None = None
        self._handle: Any | None = None
        self._platform_type = self._detect_platform()
        self._nvidia_smi_available = shutil.which("nvidia-smi") is not None
        self._init_nvml()

    def info(self) -> GPUInfo:
        """Вернуть статическую информацию о GPU."""
        return self.collect()

    def tmp(self) -> MetricStatistics | None:
        """Вернуть текущую температуру GPU в градусах Цельсия."""
        temperature = self._get_nvml_temperature()
        if temperature is None:
            temperature = self._get_smi_float("temperature.gpu")
        return self._build_metric(value=temperature, unit="celsius")

    def frq(self) -> MetricStatistics | None:
        """Вернуть текущую частоту GPU в МГц."""
        frequency = self._get_nvml_frequency()
        if frequency is None:
            frequency = self._get_smi_float("clocks.gr")
        return self._build_metric(value=frequency, unit="mhz")

    def prsnt(self) -> MetricStatistics | None:
        """Вернуть текущий процент загрузки GPU."""
        utilization = self._get_nvml_utilization()
        if utilization is None:
            utilization = self._get_smi_float("utilization.gpu")
        return self._build_metric(value=utilization, unit="percent")

    def mem(self) -> MetricStatistics | None:
        """Вернуть текущий объем занятой VRAM в мегабайтах."""
        memory_used_mb = self._get_nvml_memory_used_mb()
        if memory_used_mb is None:
            memory_used_mb = self._get_smi_float("memory.used")
        return self._build_metric(value=memory_used_mb, unit="megabyte")

    def power(self) -> MetricStatistics | None:
        """Вернуть текущее энергопотребление GPU в ваттах."""
        power_watts = self._get_nvml_power_watts()
        if power_watts is None:
            power_watts = self._get_smi_float("power.draw")
        return self._build_metric(value=power_watts, unit="watt")

    def collect(self) -> GPUInfo:
        """Вернуть статическую информацию о GPU."""
        # Сейчас реальные GPU-данные собираются через NVIDIA-инструменты.
        # Для Jetson/Raspberry Pi/Hailo ветки уже выделены через _detect_platform,
        # но платформенные источники метрик будут добавляться отдельными шагами.
        if self._is_nvml_available():
            return self._get_nvml_info()
        if self._nvidia_smi_available:
            return self._get_smi_info()
        return GPUInfo(
            name=None,
            memory_mb=None,
            driver_version=None,
            cuda_version=None,
        )

    def get_metrics(self) -> GPUMetrics:
        """Вернуть один снимок доступных runtime-метрик GPU."""
        # На неподдержанных платформах методы вернут None, а benchmark продолжит работу.
        # Это важно для Mac/Raspberry Pi/Orange Pi, где NVIDIA/NVML может отсутствовать.
        return GPUMetrics(
            vram_usage=self.mem(),
            gpu_power=self.power(),
            gpu_utilization=self.prsnt(),
            gpu_temperature=self.tmp(),
        )

    def _init_nvml(self) -> None:
        try:
            import pynvml
        except ImportError:
            return

        try:
            pynvml.nvmlInit()
            if pynvml.nvmlDeviceGetCount() == 0:
                return
            self._pynvml = pynvml
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            self._pynvml = None
            self._handle = None

    def _detect_platform(self) -> PlatformType:
        """Определить аппаратную платформу по доступным локальным признакам."""
        device_model = read_text(Path("/proc/device-tree/model")).lower()

        if "raspberry pi" in device_model:
            return PlatformType.RASPBERRY_PI

        # Orin входит в семейство Jetson, пока отдельного enum для Orin нет.
        if "jetson" in device_model or "orin" in device_model:
            return PlatformType.JETSON

        if Path("/etc/nv_tegra_release").exists():
            return PlatformType.JETSON

        if "intel nuc" in device_model:
            return PlatformType.INTEL_NUC

        if "hailo" in device_model:
            return PlatformType.HAILO

        # В текущем PlatformType нет Orange Pi. Пока оставляем UNKNOWN,
        # чтобы позже добавить отдельную ветку без ломки GPUCollector.
        if "orange pi" in device_model:
            return PlatformType.UNKNOWN

        system = platform_module.system()
        if system in {"Darwin", "Windows", "Linux"}:
            return PlatformType.DESKTOP

        return PlatformType.UNKNOWN

    def _is_nvml_available(self) -> bool:
        return self._pynvml is not None and self._handle is not None

    def _get_nvml_info(self) -> GPUInfo:
        if not self._is_nvml_available():
            return GPUInfo(None, None, None, None)

        assert self._pynvml is not None
        assert self._handle is not None

        name = self._decode_nvml_value(self._pynvml.nvmlDeviceGetName(self._handle))
        memory = self._pynvml.nvmlDeviceGetMemoryInfo(self._handle)
        driver_version = self._decode_nvml_value(self._pynvml.nvmlSystemGetDriverVersion())

        return GPUInfo(
            name=name,
            memory_mb=int(memory.total / 1024 / 1024),
            driver_version=driver_version,
            cuda_version=self._get_nvml_cuda_version(),
        )

    def _get_nvml_cuda_version(self) -> str | None:
        if self._pynvml is None:
            return None

        try:
            version = self._pynvml.nvmlSystemGetCudaDriverVersion()
        except Exception:
            return None

        major = version // 1000
        minor = (version % 1000) // 10
        return f"{major}.{minor}"

    def _get_nvml_utilization(self) -> float | None:
        if not self._is_nvml_available():
            return None

        try:
            utilization = self._pynvml.nvmlDeviceGetUtilizationRates(self._handle)
        except Exception:
            return None
        return float(utilization.gpu)

    def _get_nvml_memory_used_mb(self) -> float | None:
        if not self._is_nvml_available():
            return None

        try:
            memory = self._pynvml.nvmlDeviceGetMemoryInfo(self._handle)
        except Exception:
            return None
        return float(memory.used / 1024 / 1024)

    def _get_nvml_temperature(self) -> float | None:
        if not self._is_nvml_available():
            return None

        try:
            temperature = self._pynvml.nvmlDeviceGetTemperature(
                self._handle,
                self._pynvml.NVML_TEMPERATURE_GPU,
            )
        except Exception:
            return None
        return float(temperature)

    def _get_nvml_power_watts(self) -> float | None:
        if not self._is_nvml_available():
            return None

        try:
            power_milliwatts = self._pynvml.nvmlDeviceGetPowerUsage(self._handle)
        except Exception:
            return None
        return float(power_milliwatts / 1000)

    def _get_nvml_frequency(self) -> float | None:
        if not self._is_nvml_available():
            return None

        try:
            frequency = self._pynvml.nvmlDeviceGetClockInfo(
                self._handle,
                self._pynvml.NVML_CLOCK_GRAPHICS,
            )
        except Exception:
            return None
        return float(frequency)

    def _get_smi_info(self) -> GPUInfo:
        values = self._query_nvidia_smi("name,memory.total,driver_version")
        if values is None or len(values) < 3:
            return GPUInfo(None, None, None, None)

        return GPUInfo(
            name=values[0],
            memory_mb=to_int(values[1]),
            driver_version=values[2],
            cuda_version=None,
        )

    def _get_smi_float(self, query: str) -> float | None:
        values = self._query_nvidia_smi(query)
        if not values:
            return None
        return to_float(values[0])

    def _query_nvidia_smi(self, query: str) -> list[str] | None:
        if not self._nvidia_smi_available:
            return None

        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    f"--query-gpu={query}",
                    "--format=csv,noheader,nounits",
                    "-i",
                    "0",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=3,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        first_line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
        if not first_line:
            return None
        return [value.strip() for value in first_line.split(",")]


    def _build_metric(self, value: float | int | None, unit: str) -> MetricStatistics | None:
        if value is None:
            return None

        metric = MetricStatistics(unit=unit)
        metric.history.append(
            DataPoint(
                time_in_ms=int(time.time() * 1000),
                value=value,
            )
        )
        return metric


    def _decode_nvml_value(self, value: bytes | str) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return value

