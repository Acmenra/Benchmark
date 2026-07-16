# tests/test_temperature.py

import logging
import pytest

from infrastructure.hardware.collectors.base import is_valid_temperature
from infrastructure.hardware.collectors.cpu import (
    collect_cpu,
    is_temperature_sensor_available as is_cpu_temperature_sensor_available,
    get_cpu_temperature,
)
from infrastructure.hardware.collectors.gpu import (
    collect_gpu,
    is_temperature_sensor_available as is_gpu_temperature_sensor_available,
    GPUCollector,
)
from infrastructure.hardware.collectors.npu import NPUCollector
from infrastructure.hardware.collectors.mps import MPSCollector
from core.entities.hardware import CPUInfo, GPUInfo


logger = logging.getLogger(__name__)


def test_collect_cpu_includes_temperature_sensor_availability() -> None:
    """collect_cpu должен включать информацию о доступности датчика температуры."""
    cpu_info = collect_cpu()

    assert isinstance(cpu_info, CPUInfo)
    assert isinstance(cpu_info.temperature_sensor_available, bool)


def test_collect_gpu_includes_temperature_sensor_availability() -> None:
    """collect_gpu должен включать информацию о доступности датчика температуры."""
    gpu_info = collect_gpu()

    assert isinstance(gpu_info, GPUInfo)
    assert isinstance(gpu_info.temperature_sensor_available, bool)


def test_cpu_temperature_sensor_availability_is_boolean() -> None:
    """Поле temperature_sensor_available в CPUInfo должно быть булевым."""
    cpu_info = collect_cpu()

    assert cpu_info.temperature_sensor_available in (True, False)


def test_gpu_temperature_sensor_availability_is_boolean() -> None:
    """Поле temperature_sensor_available в GPUInfo должно быть булевым."""
    gpu_info = collect_gpu()

    assert gpu_info.temperature_sensor_available in (True, False)


def test_cpu_info_is_frozen() -> None:
    """CPUInfo должен быть неизменяемым."""
    cpu_info = collect_cpu()

    with pytest.raises(AttributeError):
        cpu_info.temperature_sensor_available = False


def test_gpu_info_is_frozen() -> None:
    """GPUInfo должен быть неизменяемым."""
    gpu_info = collect_gpu()

    with pytest.raises(AttributeError):
        gpu_info.temperature_sensor_available = False


def test_cpu_info_has_temperature_sensor_slot() -> None:
    """CPUInfo должен иметь поле temperature_sensor_available."""
    cpu_info = collect_cpu()

    assert hasattr(CPUInfo, "__slots__")
    assert "temperature_sensor_available" in CPUInfo.__slots__


def test_gpu_info_has_temperature_sensor_slot() -> None:
    """GPUInfo должен иметь поле temperature_sensor_available."""
    gpu_info = collect_gpu()

    assert hasattr(GPUInfo, "__slots__")
    assert "temperature_sensor_available" in GPUInfo.__slots__


def test_is_valid_temperature_valid_values() -> None:
    """Проверка обработки валидных значений."""
    assert is_valid_temperature(0) is True
    assert is_valid_temperature(20) is True
    assert is_valid_temperature(25.5) is True
    assert is_valid_temperature(50) is True
    assert is_valid_temperature(75.3) is True
    assert is_valid_temperature(100) is True
    assert is_valid_temperature(149.9) is True


def test_is_valid_temperature_invalid_values() -> None:
    """Проверка отклонения невалидных значений."""
    assert is_valid_temperature(-1) is False
    assert is_valid_temperature(-50) is False
    assert is_valid_temperature(-273.15) is False
    assert is_valid_temperature(150) is False
    assert is_valid_temperature(200) is False
    assert is_valid_temperature(500) is False
    assert is_valid_temperature(5000) is False


def test_is_valid_temperature_invalid_types() -> None:
    """Проверка отклонения невалидных типов данных."""
    assert is_valid_temperature("50") is False
    assert is_valid_temperature("temperature") is False
    assert is_valid_temperature(None) is False
    assert is_valid_temperature([50]) is False
    assert is_valid_temperature({"temp": 50}) is False


def test_is_valid_temperature_boundary_values() -> None:
    """Проверка граничных значений диапазона."""
    assert is_valid_temperature(0) is True
    assert is_valid_temperature(0.0) is True
    assert is_valid_temperature(149.99999) is True
    assert is_valid_temperature(150) is False
    assert is_valid_temperature(150.00001) is False


def test_cpu_temperature_check_returns_boolean() -> None:
    """is_cpu_temperature_sensor_available должна возвращать boolean."""
    result = is_cpu_temperature_sensor_available()
    assert isinstance(result, bool)


def test_gpu_temperature_check_returns_boolean() -> None:
    """is_gpu_temperature_sensor_available должна возвращать boolean."""
    result = is_gpu_temperature_sensor_available()
    assert isinstance(result, bool)


def test_collect_cpu_temperature_consistency() -> None:
    """Проверка согласованности результатов CPU."""
    cpu1 = collect_cpu()
    cpu2 = collect_cpu()
    cpu3 = collect_cpu()

    assert (
        cpu1.temperature_sensor_available
        == cpu2.temperature_sensor_available
        == cpu3.temperature_sensor_available
    )


def test_collect_gpu_temperature_consistency() -> None:
    """Проверка согласованности результатов GPU."""
    gpu1 = collect_gpu()
    gpu2 = collect_gpu()
    gpu3 = collect_gpu()

    assert (
        gpu1.temperature_sensor_available
        == gpu2.temperature_sensor_available
        == gpu3.temperature_sensor_available
    )


def test_collect_cpu_on_known_system() -> None:
    """Проверка безошибочной работы CPU на известной системе."""
    try:
        cpu_info = collect_cpu()
        assert isinstance(cpu_info, CPUInfo)
        assert isinstance(cpu_info.temperature_sensor_available, bool)
    except Exception as e:
        pytest.fail(f"collect_cpu() raised {type(e).__name__}: {e}")


def test_collect_gpu_on_known_system() -> None:
    """Проверка безошибочной работы GPU на известной системе."""
    try:
        gpu_info = collect_gpu()
        assert isinstance(gpu_info, GPUInfo)
        assert isinstance(gpu_info.temperature_sensor_available, bool)
    except Exception as e:
        pytest.fail(f"collect_gpu() raised {type(e).__name__}: {e}")


def test_cpu_info_dataclass_fields() -> None:
    """Проверка наличия поля temperature_sensor_available в CPUInfo."""
    from dataclasses import fields

    field_names = {f.name for f in fields(CPUInfo)}
    assert "temperature_sensor_available" in field_names


def test_gpu_info_dataclass_fields() -> None:
    """Проверка наличия поля temperature_sensor_available в GPUInfo."""
    from dataclasses import fields

    field_names = {f.name for f in fields(GPUInfo)}
    assert "temperature_sensor_available" in field_names


def test_cpu_info_creation_with_temperature_sensor() -> None:
    """Проверка создания CPUInfo с полем temperature_sensor_available."""
    cpu_info = CPUInfo(
        name="Test CPU",
        architecture="x86_64",
        physical_cores=4,
        logical_cores=8,
        max_frequency_mhz=3000.0,
        temperature_sensor_available=True,
    )

    assert cpu_info.temperature_sensor_available is True


def test_gpu_info_creation_with_temperature_sensor() -> None:
    """Проверка создания GPUInfo с полем temperature_sensor_available."""
    gpu_info = GPUInfo(
        name="Test GPU",
        memory_mb=8192,
        driver_version="535.0",
        has_cuda=True,
        cuda_version="12.0",
        temperature_sensor_available=False,
    )

    assert gpu_info.temperature_sensor_available is False


def test_cpu_temperature_sensor_matches_reading() -> None:
    """Доступность датчика CPU должна соответствовать возможности прочитать температуру."""
    sensor_available = is_cpu_temperature_sensor_available()
    temperature = get_cpu_temperature()

    assert sensor_available == (temperature is not None)


def test_gpu_temperature_sensor_matches_reading() -> None:
    """Доступность датчика GPU должна соответствовать возможности прочитать температуру."""
    collector = GPUCollector()
    sensor_available = collector.is_temperature_sensor_available()
    temperature = collector.tmp()

    assert sensor_available == (temperature is not None and is_valid_temperature(temperature))


def test_npu_collector_temperature_check_returns_boolean() -> None:
    """NPUCollector.is_temperature_sensor_available должна возвращать boolean."""
    collector = NPUCollector()
    result = collector.is_temperature_sensor_available()
    assert isinstance(result, bool)


def test_mps_collector_temperature_check_returns_boolean() -> None:
    """MPSCollector.is_temperature_sensor_available должна возвращать boolean."""
    collector = MPSCollector()
    result = collector.is_temperature_sensor_available()
    assert isinstance(result, bool)
