"""Замер энергопотребления и температуры с graceful degradation по платформам.

Источники (в порядке попытки):
- Jetson: файлы ``/sys/bus/i2c/drivers/ina3221x/*/in_power*_input`` (питание),
  ``/sys/class/thermal/thermal_zone*/temp`` (температура).
- Raspberry Pi: `vcgencmd measure_temp` (температура SoC), затем тот же
  ``thermal_zone`` (там зона называется ``cpu-thermal``).
- Десктоп с NVIDIA GPU: `pynvml` (опционально).
- Иначе: `psutil.sensors_temperatures()` (только Linux) для CPU-температуры.

Если ничего не доступно (типично для Windows без сенсоров) — возвращается
`PowerResult(unsupported=True)`, без исключений.
"""

from __future__ import annotations

import glob
import logging
from pathlib import Path

import psutil

from edge_ai_benchmark.core.entities import PowerResult

logger = logging.getLogger(__name__)

try:
    import pynvml as _pynvml
except ImportError:
    _pynvml = None


def _read_jetson_power_w() -> float | None:
    paths = glob.glob("/sys/bus/i2c/drivers/ina3221x/*/in_power*_input")
    if not paths:
        return None
    total_mw = 0.0
    found = False
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                total_mw += float(fh.read().strip())
                found = True
        except (OSError, ValueError):
            logger.debug("Не удалось прочитать %s", path, exc_info=True)
    return (total_mw / 1000.0) if found else None


def _read_gpu_power_w() -> float | None:
    if _pynvml is None:
        return None
    try:
        _pynvml.nvmlInit()
        try:
            handle = _pynvml.nvmlDeviceGetHandleByIndex(0)
            return _pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
        finally:
            _pynvml.nvmlShutdown()
    except Exception:
        logger.debug("Не удалось получить мощность GPU через pynvml", exc_info=True)
        return None


def get_power_consumption() -> PowerResult:
    """Замерить текущее энергопотребление системы/GPU.

    Returns:
        `PowerResult` с заполненным `power_w`, либо `unsupported=True`,
        если ни один источник не доступен на этой платформе.
    """
    power_w = _read_jetson_power_w()
    if power_w is None:
        power_w = _read_gpu_power_w()

    if power_w is None:
        return PowerResult(unsupported=True)
    return PowerResult(power_w=power_w)


def _read_thermal_zone_c(keywords: tuple[str, ...]) -> float | None:
    """Найти зону `/sys/class/thermal/thermal_zone*`, чьё имя содержит одно из `keywords`.

    Универсальный Linux ARM-механизм (не только Jetson): каждая термозона
    поименована в файле ``.../type`` (например ``CPU-therm``/``GPU-therm`` на
    Jetson, ``cpu-thermal`` на Raspberry Pi OS), а значение температуры (в
    миллиградусах Цельсия) лежит в соседнем файле ``.../temp``. На платформах
    без такой структуры (Windows) `glob` просто ничего не найдёт.

    Args:
        keywords: Ключевые слова для поиска в имени зоны (регистронезависимо),
            например ``("cpu",)`` или ``("gpu",)``.

    Returns:
        Температура в градусах Цельсия, либо `None`, если подходящая зона не найдена.
    """
    for type_path in glob.glob("/sys/class/thermal/thermal_zone*/type"):
        try:
            with open(type_path, encoding="utf-8") as fh:
                zone_type = fh.read().strip().lower()
        except OSError:
            continue
        if not any(kw in zone_type for kw in keywords):
            continue
        # Не строковая замена "/type"->"/temp" (ломается на Windows-путях с
        # обратным слэшем в тестах) — берём соседний файл через pathlib.
        temp_path = Path(type_path).with_name("temp")
        try:
            millidegrees = float(temp_path.read_text(encoding="utf-8").strip())
            return millidegrees / 1000.0
        except (OSError, ValueError):
            logger.debug("Не удалось прочитать %s", temp_path, exc_info=True)
    return None


def _read_vcgencmd_temp_c() -> float | None:
    """Прочитать температуру SoC через `vcgencmd measure_temp` (Raspberry Pi OS).

    Официальная утилита Raspberry Pi для чтения датчика температуры SoC —
    точнее и всегда доступна на RPi (в отличие от имени thermal_zone, которое
    менялось между версиями Raspberry Pi OS). На других платформах команды
    просто нет — тихо возвращаем `None`.

    Returns:
        Температура в градусах Цельсия, либо `None`, если `vcgencmd`
        недоступен или вернул неожиданный вывод.
    """
    import subprocess

    try:
        output = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None

    # Формат вывода: "temp=42.8'C"
    try:
        return float(output.strip().split("=")[1].split("'")[0])
    except (IndexError, ValueError):
        logger.debug("Неожиданный вывод vcgencmd measure_temp: %r", output)
        return None


def _read_gpu_temperature_c() -> float | None:
    zone_temp = _read_thermal_zone_c(("gpu",))
    if zone_temp is not None:
        return zone_temp

    if _pynvml is None:
        return None
    try:
        _pynvml.nvmlInit()
        try:
            handle = _pynvml.nvmlDeviceGetHandleByIndex(0)
            return float(_pynvml.nvmlDeviceGetTemperature(handle, _pynvml.NVML_TEMPERATURE_GPU))
        finally:
            _pynvml.nvmlShutdown()
    except Exception:
        logger.debug("Не удалось получить температуру GPU через pynvml", exc_info=True)
        return None


def _read_cpu_temperature_c() -> float | None:
    vcgencmd_temp = _read_vcgencmd_temp_c()
    if vcgencmd_temp is not None:
        return vcgencmd_temp

    zone_temp = _read_thermal_zone_c(("cpu",))
    if zone_temp is not None:
        return zone_temp

    sensors_fn = getattr(psutil, "sensors_temperatures", None)
    if sensors_fn is None:
        return None
    try:
        sensors = sensors_fn()
    except Exception:
        logger.debug("psutil.sensors_temperatures() недоступен", exc_info=True)
        return None
    for readings in sensors.values():
        if readings:
            return float(readings[0].current)
    return None


def get_temperature() -> PowerResult:
    """Замерить температуру CPU/GPU.

    Порядок источников для CPU: `vcgencmd` (Raspberry Pi) -> thermal_zone
    (Jetson/RPi/generic ARM Linux) -> `psutil.sensors_temperatures`.
    Для GPU: thermal_zone (Jetson) -> `pynvml` (NVIDIA).

    Returns:
        `PowerResult` с заполненными `cpu_temperature_c`/`gpu_temperature_c`,
        либо `unsupported=True`, если ни один датчик не доступен.
    """
    gpu_temp = _read_gpu_temperature_c()
    cpu_temp = _read_cpu_temperature_c()

    if gpu_temp is None and cpu_temp is None:
        return PowerResult(unsupported=True)
    return PowerResult(gpu_temperature_c=gpu_temp, cpu_temperature_c=cpu_temp)
