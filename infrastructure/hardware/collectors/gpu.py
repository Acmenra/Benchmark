# infrastructure/hardware/collectors/gpu.py

import logging
from pathlib import Path
import re
import shutil
import subprocess

from core.entities.config import SystemInfoConfig

logger = logging.getLogger(__name__)

import pynvml
import platform

from core.entities.hardware import GPUInfo
from infrastructure.hardware.collectors.base import BaseCollector


class GPUCollector(BaseCollector):
    def __init__(self, system_info_config: SystemInfoConfig):
        self.system_info_config = system_info_config

    def info(self) -> GPUInfo:
        if self._pynvml_available():
            return self._info_pynvml()

        if self._nvidia_smi_available():
            return self._info_nvidia_smi()

        return GPUInfo(
            name=None,
            memory_mb=None,
            driver_version=None,
            has_cuda=False,
            cuda_version=None,
        )

    def tmp(self) -> float | None:
        if self._jetson():
            return self._temperature_tegrastats()
        
        if self._pynvml_available():
            return self._temperature_pynvml()

        if self._nvidia_smi_available():
            return self._query_nvidia_smi("temperature.gpu")
        
        if platform.system() == "Linux":
            return self._temperature_hwmon()

        return None

    def frq(self) -> float | None:
        if self._jetson():
            return self._frq_tegrastats()
        
        if self._pynvml_available():
            return self._frq_pynvml()
        
        if self._nvidia_smi_available():
            return self._query_nvidia_smi("clocks.current.graphics")
        
        if platform.system() == "Linux":
            return self._frq_linux()
        
        return None
    
    def prsnt(self) -> ...:
        pass

    def mem(self) -> float | None:
        if self._jetson():
            return self._mem_tegrastats()
        
        if self._pynvml_available():
            return self._mem_pynvml()
        
        if self._nvidia_smi_available():
            return self._query_nvidia_smi("memory.used")
        
        if platform.system() == "Linux":
            return self._mem_linux()
        
        return None


    def power(self) -> float | None:
        if self._pynvml_available():
            return self._power_pynvml()
        
        if self._nvidia_smi_available():
            return self._query_nvidia_smi("power.draw")
        
        if platform.system() == "Linux":
            return self._power_linux()
        
        return None

#             <---------- доступность драйверов ---------->

    def _pynvml_available(self) -> bool:
        try:
            pynvml.nvmlInit()
            pynvml.nvmlShutdown()
            return True
        except:
            return False

    def _nvidia_smi_available(self) -> bool:
        try:
            if shutil.which("nvidia-smi") is None:
                return False

            result = subprocess.run(
                ["nvidia-smi", "-L"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            return False

    def _jetson(self) -> bool:
        return (
            Path("/etc/nv_tegra_release").exists()
            or Path("/proc/device-tree/model").read_text(
                errors="ignore"
            ).lower().find("nvidia jetson") >= 0
        )

#             <---------- информация о GPU ---------->

    def _info_pynvml(self) -> GPUInfo:
        pynvml.nvmlInit()

        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        memory_mb = int(int(memory.total) / (1024 ** 2))
        driver_version = pynvml.nvmlSystemGetDriverVersion()
        cuda_version = str(pynvml.nvmlSystemGetCudaDriverVersion_v2())

        pynvml.nvmlShutdown()

        return GPUInfo(
            name=name,
            memory_mb=memory_mb,
            driver_version=driver_version,
            has_cuda=True,
            cuda_version=cuda_version
        )

    def _info_nvidia_smi(self) -> GPUInfo:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return GPUInfo()

        line = result.stdout.strip().splitlines()[0]

        name, memory, driver = [
            value.strip()
            for value in line.split(",")
        ]

        return GPUInfo(
            name=name,
            memory_mb=int(memory),
            driver_version=driver,
            has_cuda=True,
            cuda_version=self._cuda_version_nvidia_smi(),
        )

    def _cuda_version_nvidia_smi(self) -> str | None:
        result = subprocess.run(
            [
                "nvidia-smi",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return None

        match = re.search(
            r"CUDA Version:\s+(\d+\.\d+)",
            result.stdout,
        )

        if match:
            return match.group(1)

        return None
    
#             <---------- nvidea smi ---------->

    def _query_nvidia_smi(self, query: str) -> float | None:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    f"--query-gpu={query}",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return None

            return float(result.stdout.strip().splitlines()[0])
        except:
            return None

#             <---------- ТЕМПЕРАТУРА ---------->

    def _temperature_pynvml(self) -> float:
        pynvml.nvmlInit()

        # берется первая видеокарта
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

        pynvml.nvmlShutdown()
        
        return temperature

    def _temperature_hwmon(self) -> float | None:
        hwmon_root = Path("/sys/class/hwmon")
        if not hwmon_root.exists():
            return None

        gpu_driver_names = (
            "nvidia",
            "amdgpu",
            "radeon",
            "i915",
            "nouveau",
        )

        for hwmon_dir in hwmon_root.iterdir():
            try:
                name_file = hwmon_dir / "name"
                if not name_file.exists():
                    continue

                driver_name = name_file.read_text(encoding="utf-8", errors="ignore").strip().lower()

                if not any(token in driver_name for token in gpu_driver_names):
                    continue

                for temp_input in sorted(hwmon_dir.glob("temp*_input")):
                    try:
                        raw_value = temp_input.read_text(encoding="utf-8", errors="ignore").strip()
                        return float(raw_value) / 1000.0
                    except:
                        continue
            except:
                continue
 
        return None

    def _temperature_tegrastats(self) -> float | None:
        process = None

        try:
            process = subprocess.Popen(
                ["tegrastats", "--interval", "1000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )

            if process.stdout is None:
                return None
            line = process.stdout.readline()

            match = re.search(
                r"GPU@(\d+)C",
                line
            )

            if match:
                return float(match.group(1))
        except:
            pass
        finally:
            if process:
                process.terminate()

        return None
    
#             <---------- ЧАСТОТА ---------->

    def _frq_pynvml(self) -> float:
        pynvml.nvmlInit()

        # берется первая видеокарта
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        frq = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_SM) 

        pynvml.nvmlShutdown()

        return frq         # возвращает значение в МГц

    def _frq_tegrastats(self) -> float | None:
        process = None

        try:
            process = subprocess.Popen(
                ["tegrastats"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )

            if process.stdout is None:
                return None
            line = process.stdout.readline()

            match = re.search(r"GR3D_FREQ \d+%@(\d+)", line)
            if match:
                return float(match.group(1))

        except:
            pass

        finally:
            if process is not None:
                process.terminate()

        return None

    def _frq_linux(self) -> float | None:
        frequency_files = (
            Path("/sys/class/drm/card0/device/pp_dpm_sclk"),     # AMD
            Path("/sys/class/drm/card0/gt_cur_freq_mhz"),        # Intel
        )

        for path in frequency_files:
            if not path.exists():
                continue

            try:
                if path.name == "gt_cur_freq_mhz":
                    return float(path.read_text().strip())

                if path.name == "pp_dpm_sclk":
                    for line in path.read_text().splitlines():
                        if "*" in line:
                            value = line.split(":")[1].split("Mhz")[0].strip()
                            return float(value)
            except:
                continue

        return None

#             <---------- ПАМЯТЬ ---------->

    def _mem_tegrastats(self) -> None:
        # Jetson использует общую оперативную память (UMA).
        # Tegrastats не предоставляет объем памяти,
        # используемой только GPU.
        return None

    def _mem_pynvml(self) -> float | None:
        pynvml.nvmlInit()

        # берется первая видеокарта
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)

        pynvml.nvmlShutdown()

        return int(memory.used) / (1024 ** 2)  # возвращает занятое значение в MB

    def _mem_linux(self) -> float | None:
        # AMD
        vram_used = Path("/sys/class/drm/card0/device/mem_info_vram_used")
        if vram_used.exists():
            try:
                return int(vram_used.read_text().strip()) / (1024 ** 2)  # MB
            except:
                pass

        return None # другие драйверы не предоставляют универсального интерфейса

#             <---------- ЭНЕРГИЯ ---------->

    def _power_pynvml(self) -> float:
        pynvml.nvmlInit()

        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        power = pynvml.nvmlDeviceGetPowerUsage(handle) # милливаттах

        pynvml.nvmlShutdown()

        return power / 1000

    def _power_linux(self) -> float | None:
        # актуально только для AMD
        hwmon_root = Path("/sys/class/hwmon")
        if not hwmon_root.exists():
            return None

        gpu_driver_names = (
            "amdgpu",
        )

        for hwmon_dir in hwmon_root.iterdir():
            try:
                name_file = hwmon_dir / "name"
                if not name_file.exists():
                    continue

                driver_name = name_file.read_text().strip().lower()

                if driver_name not in gpu_driver_names:
                    continue

                power_file = hwmon_dir / "power1_average"
                if not power_file.exists():
                    continue

                return int(power_file.read_text().strip()) / 1_000_000 # возвращает в W

            except (OSError, ValueError):
                continue

        return None

