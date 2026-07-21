"""Сбор характеристик железа и системы.

Все функции здесь реализованы с graceful degradation: опциональные библиотеки
(`py-cpuinfo`, `pynvml`) импортируются в try/except, а недоступное железо
(GPU, специфичные для платформы файлы в /proc, /sys) приводит к `None`/пустым
значениям в результате, а не к исключению.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import sys
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)

try:
    import cpuinfo as _py_cpuinfo
except ImportError:
    _py_cpuinfo = None

try:
    import pynvml as _pynvml
except ImportError:
    _pynvml = None


def get_os_info() -> dict[str, Any]:
    """Собрать информацию об операционной системе.

    Returns:
        Словарь с ключами ``os``, ``system``, ``release``.
    """
    return {
        "os": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
    }


def get_python_info() -> dict[str, Any]:
    """Собрать информацию о версии Python и архитектуре процесса.

    Returns:
        Словарь с ключами ``python_version``, ``architecture``.
    """
    return {
        "python_version": platform.python_version(),
        "architecture": platform.machine() or sys.maxsize.bit_length(),
    }


def _parse_cache_size_to_kb(value: Any) -> int | None:
    """Привести значение размера кэша (int в байтах либо строка "256 KiB") к KB."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) // 1024
    match = re.match(r"([\d.]+)\s*([KMG]?i?B)?", str(value).strip())
    if not match:
        return None
    number = float(match.group(1))
    unit = (match.group(2) or "KB").upper()
    if unit.startswith("G"):
        return int(number * 1024 * 1024)
    if unit.startswith("M"):
        return int(number * 1024)
    if unit.startswith("K"):
        return int(number)
    return int(number / 1024)


def get_cpu_cache_info() -> dict[str, int | None]:
    """Собрать размеры кэшей CPU (L1/L2/L3) в килобайтах.

    Использует `py-cpuinfo`, если он установлен; иначе возвращает `None`
    для всех уровней (нет переносимого способа получить кэши только через
    стандартную библиотеку).

    Returns:
        Словарь ``{"l1_kb": ..., "l2_kb": ..., "l3_kb": ...}``.
    """
    if _py_cpuinfo is None:
        logger.debug("py-cpuinfo не установлен — размеры кэша CPU недоступны")
        return {"l1_kb": None, "l2_kb": None, "l3_kb": None}

    try:
        info = _py_cpuinfo.get_cpu_info()
    except Exception:
        logger.warning("Не удалось получить cpuinfo", exc_info=True)
        return {"l1_kb": None, "l2_kb": None, "l3_kb": None}

    l1_data = _parse_cache_size_to_kb(info.get("l1_data_cache_size"))
    l1_instr = _parse_cache_size_to_kb(info.get("l1_instruction_cache_size"))
    l1_kb = None
    if l1_data is not None or l1_instr is not None:
        l1_kb = (l1_data or 0) + (l1_instr or 0)

    return {
        "l1_kb": l1_kb,
        "l2_kb": _parse_cache_size_to_kb(info.get("l2_cache_size")),
        "l3_kb": _parse_cache_size_to_kb(info.get("l3_cache_size")),
    }


def get_cpu_info() -> dict[str, Any]:
    """Собрать подробную информацию о CPU: модель, ядра, частота, кэши.

    Returns:
        Словарь с ключами ``model``, ``architecture``, ``physical_cores``,
        ``logical_cores``, ``frequency_current_mhz``, ``frequency_max_mhz``,
        ``cache``.
    """
    model = platform.processor() or "unknown"
    if _py_cpuinfo is not None:
        try:
            model = _py_cpuinfo.get_cpu_info().get("brand_raw", model)
        except Exception:
            logger.warning("Не удалось получить модель CPU из py-cpuinfo", exc_info=True)

    freq = None
    try:
        freq = psutil.cpu_freq()
    except Exception:
        logger.debug("psutil.cpu_freq() недоступен на этой платформе", exc_info=True)

    return {
        "model": model,
        "architecture": platform.machine(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "frequency_current_mhz": getattr(freq, "current", None),
        "frequency_max_mhz": getattr(freq, "max", None) or None,
        "cache": get_cpu_cache_info(),
    }


def get_ram_info() -> dict[str, Any]:
    """Собрать информацию об оперативной памяти.

    Returns:
        Словарь с ключами ``total_gb``, ``available_gb``, ``used_gb``.
    """
    vm = psutil.virtual_memory()
    return {
        "total_gb": round(vm.total / (1024**3), 2),
        "available_gb": round(vm.available / (1024**3), 2),
        "used_gb": round(vm.used / (1024**3), 2),
    }


def get_disk_info(path: str | os.PathLike = ".") -> dict[str, Any]:
    """Собрать информацию о диске, на котором расположен `path`.

    Args:
        path: Путь, для которого определяется диск (по умолчанию — текущая директория).

    Returns:
        Словарь с ключами ``device``, ``filesystem``, ``total_gb``, ``used_gb``, ``free_gb``.
    """
    resolved = str(Path(path).resolve())
    device = resolved
    filesystem = None
    try:
        for part in psutil.disk_partitions(all=False):
            if resolved.startswith(part.mountpoint):
                device = part.device
                filesystem = part.fstype
                break
    except Exception:
        logger.debug("Не удалось получить список разделов диска", exc_info=True)

    usage = psutil.disk_usage(resolved)
    return {
        "device": device,
        "filesystem": filesystem,
        "total_gb": round(usage.total / (1024**3), 2),
        "used_gb": round(usage.used / (1024**3), 2),
        "free_gb": round(usage.free / (1024**3), 2),
    }


def _nvml_context():
    """Контекстный менеджер, инициализирующий NVML и гарантированно завершающий его."""
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        _pynvml.nvmlInit()
        try:
            yield
        finally:
            _pynvml.nvmlShutdown()

    return _ctx()


def get_gpu_info() -> dict[str, Any]:
    """Собрать информацию о первом обнаруженном NVIDIA GPU через `pynvml`.

    Returns:
        Словарь с ``available: bool`` и, если доступен, ``model``,
        ``vram_total_gb``, ``driver_version``, ``cuda_version``.
    """
    if _pynvml is None:
        logger.debug("pynvml не установлен — информация о GPU недоступна")
        return {"available": False}

    try:
        with _nvml_context():
            handle = _pynvml.nvmlDeviceGetHandleByIndex(0)
            name = _pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode()
            mem = _pynvml.nvmlDeviceGetMemoryInfo(handle)
            driver = _pynvml.nvmlSystemGetDriverVersion()
            if isinstance(driver, bytes):
                driver = driver.decode()
            cuda_version = None
            try:
                cuda_raw = _pynvml.nvmlSystemGetCudaDriverVersion()
                cuda_version = f"{cuda_raw // 1000}.{(cuda_raw % 1000) // 10}"
            except Exception:
                logger.debug("CUDA driver version недоступна", exc_info=True)

            return {
                "available": True,
                "model": name,
                "vram_total_gb": round(mem.total / (1024**3), 2),
                "driver_version": driver,
                "cuda_version": cuda_version,
            }
    except Exception:
        logger.info("NVIDIA GPU не обнаружен или недоступен", exc_info=True)
        return {"available": False}


def _is_openvino_available() -> bool:
    """Проверить доступность OpenVINO независимо от версии его API.

    openvino>=2024 переместил ``Core`` из ``openvino.runtime`` в сам пакет
    ``openvino``; более старые версии держат его только в ``openvino.runtime``.
    Проверка только через ``import openvino.runtime`` даёт ложный ``False``
    на новых версиях (см. тот же фикс в
    `infrastructure.models.openvino_loader`).
    """
    try:
        import openvino  # noqa: F401

        return True
    except ImportError:
        return False


def get_accelerators_info() -> dict[str, bool]:
    """Определить доступность ускорителей инференса (TensorRT/OpenVINO/Hailo RT).

    Returns:
        Словарь ``{"tensorrt": bool, "openvino": bool, "hailo_rt": bool}``.
    """
    accelerators = {"openvino": _is_openvino_available()}
    for key, module_name in (
        ("tensorrt", "tensorrt"),
        ("hailo_rt", "hailo_platform"),
    ):
        try:
            __import__(module_name)
            accelerators[key] = True
        except ImportError:
            accelerators[key] = False
    return accelerators


def detect_platform() -> str:
    """Определить тип платформы: desktop / jetson / raspberry_pi / unknown.

    Returns:
        Строковое значение `core.enums.PlatformType`.
    """
    from edge_ai_benchmark.core.enums import PlatformType

    if platform.system() != "Linux":
        return PlatformType.DESKTOP.value

    model_path = Path("/proc/device-tree/model")
    if model_path.is_file():
        try:
            model = model_path.read_text(errors="ignore").strip("\x00").lower()
        except OSError:
            model = ""
        if "jetson" in model or "nvidia" in model:
            return PlatformType.JETSON.value
        if "raspberry pi" in model:
            return PlatformType.RASPBERRY_PI.value

    return PlatformType.DESKTOP.value


def collect_system_info(
    collect_cpu: bool = True,
    collect_ram: bool = True,
    collect_disk: bool = True,
    collect_gpu: bool = True,
    disk_path: str | os.PathLike = ".",
) -> dict[str, Any]:
    """Собрать полную структуру характеристик системы для отчётов.

    Args:
        collect_cpu: Собирать ли подробную информацию о CPU.
        collect_ram: Собирать ли информацию об оперативной памяти.
        collect_disk: Собирать ли информацию о диске.
        collect_gpu: Собирать ли информацию о GPU.
        disk_path: Путь для определения диска (обычно — директория результатов).

    Returns:
        Словарь, соответствующий структуре ``system_info`` в отчётах README
        (``os``, ``python_version``, ``architecture``, ``platform``, ``cpu``,
        ``ram``, ``disk``, ``gpu``, ``accelerators``).
    """
    info: dict[str, Any] = {
        **get_os_info(),
        **get_python_info(),
        "platform": detect_platform(),
        "accelerators": get_accelerators_info(),
    }
    if collect_cpu:
        info["cpu"] = get_cpu_info()
    if collect_ram:
        info["ram"] = get_ram_info()
    if collect_disk:
        info["disk"] = get_disk_info(disk_path)
    if collect_gpu:
        info["gpu"] = get_gpu_info()
    return info
