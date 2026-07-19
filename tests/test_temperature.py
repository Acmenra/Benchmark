# tests/test_temperature.py

import logging
import pytest

from infrastructure.hardware.collectors.temperature import (
    collect_temperature,
    _is_valid_temperature,
    _check_cpu_temperature_available,
    _check_gpu_temperature_available,
)
from core.entities.hardware import TemperatureCapabilitiesInfo


logger = logging.getLogger(__name__)


def test_collect_temperature_returns_temperature_capabilities_info() -> None:
    """collect_temperature должен возвращать TemperatureCapabilitiesInfo."""
    temp_info = collect_temperature()
    
    assert isinstance(temp_info, TemperatureCapabilitiesInfo)
    assert isinstance(temp_info.cpu_sensor_available, bool)
    assert isinstance(temp_info.gpu_sensor_available, bool)


def test_temperature_capabilities_values_are_boolean() -> None:
    """Оба поля должны содержать булевы значения."""
    temp_info = collect_temperature()
    
    assert temp_info.cpu_sensor_available in (True, False)
    assert temp_info.gpu_sensor_available in (True, False)


def test_temperature_capabilities_is_frozen() -> None:
    """TemperatureCapabilitiesInfo должен быть неизменяемым."""
    temp_info = collect_temperature()
    
    with pytest.raises(AttributeError):
        temp_info.cpu_sensor_available = False


def test_temperature_capabilities_has_slots() -> None:
    """TemperatureCapabilitiesInfo должен иметь __slots__ для экономии памяти."""
    temp_info = collect_temperature()
    
    # Проверка, что __slots__ определены
    assert hasattr(TemperatureCapabilitiesInfo, '__slots__')
    assert 'cpu_sensor_available' in TemperatureCapabilitiesInfo.__slots__
    assert 'gpu_sensor_available' in TemperatureCapabilitiesInfo.__slots__
    
    # Проверка, что нельзя добавить новые атрибуты
    with pytest.raises((AttributeError, TypeError)):
        temp_info.new_attribute = True


def test_is_valid_temperature_valid_values() -> None:
    """Проверка обработки валидных значений."""
    # Минимальная температура
    assert _is_valid_temperature(0) is True
    
    # Комнатная температура
    assert _is_valid_temperature(20) is True
    assert _is_valid_temperature(25.5) is True
    
    # Допустимая температура
    assert _is_valid_temperature(50) is True
    assert _is_valid_temperature(75.3) is True
    
    # Максимальная температура
    assert _is_valid_temperature(100) is True
    assert _is_valid_temperature(149.9) is True


def test_is_valid_temperature_invalid_values() -> None:
    """Проверка отклонения невалидных значений."""
    # Отрицательные значения
    assert _is_valid_temperature(-1) is False
    assert _is_valid_temperature(-50) is False
    assert _is_valid_temperature(-273.15) is False
    
    # Слишком высокие значения
    assert _is_valid_temperature(150) is False
    assert _is_valid_temperature(200) is False
    assert _is_valid_temperature(500) is False
    assert _is_valid_temperature(5000) is False


def test_is_valid_temperature_invalid_types() -> None:
    """Проверка отклонения невалидных типов данных."""
    # String
    assert _is_valid_temperature("50") is False
    assert _is_valid_temperature("temperature") is False
    
    # None
    assert _is_valid_temperature(None) is False
    
    # List, dict
    assert _is_valid_temperature([50]) is False
    assert _is_valid_temperature({"temp": 50}) is False


def test_is_valid_temperature_boundary_values() -> None:
    """Проверка граничных значений диапазона."""
    # Нижняя граница (включена)
    assert _is_valid_temperature(0) is True
    assert _is_valid_temperature(0.0) is True
    
    # Верхняя граница (исключена)
    assert _is_valid_temperature(149.99999) is True
    assert _is_valid_temperature(150) is False
    assert _is_valid_temperature(150.00001) is False


def test_cpu_temperature_check_returns_boolean() -> None:
    """_check_cpu_temperature_available должна возвращать boolean."""
    result = _check_cpu_temperature_available()
    assert isinstance(result, bool)


def test_gpu_temperature_check_returns_boolean() -> None:
    """_check_gpu_temperature_available должна возвращать boolean."""
    result = _check_gpu_temperature_available()
    assert isinstance(result, bool)


def test_collect_temperature_consistency() -> None:
    """Проверка согласованности результатов."""
    temp1 = collect_temperature()
    temp2 = collect_temperature()
    temp3 = collect_temperature()
    
    # Результаты должны быть одинаковыми (датчики не появляются/исчезают)
    assert temp1.cpu_sensor_available == temp2.cpu_sensor_available == temp3.cpu_sensor_available
    assert temp1.gpu_sensor_available == temp2.gpu_sensor_available == temp3.gpu_sensor_available


def test_collect_temperature_on_known_system() -> None:
    """Проверка безошибочной работы на известной системе."""
    try:
        temp_info = collect_temperature()
        assert isinstance(temp_info, TemperatureCapabilitiesInfo)
        assert isinstance(temp_info.cpu_sensor_available, bool)
        assert isinstance(temp_info.gpu_sensor_available, bool)
    except Exception as e:
        pytest.fail(f"collect_temperature() raised {type(e).__name__}: {e}")


def test_temperature_capabilities_info_dataclass_fields() -> None:
    """Проверка правильности полей в TemperatureCapabilitiesInfo."""
    from dataclasses import fields
    
    field_names = {f.name for f in fields(TemperatureCapabilitiesInfo)}
    assert field_names == {'cpu_sensor_available', 'gpu_sensor_available'}


def test_temperature_capabilities_info_is_dataclass() -> None:
    """Проверка, что TemperatureCapabilitiesInfo является dataclass."""
    from dataclasses import is_dataclass
    
    assert is_dataclass(TemperatureCapabilitiesInfo)


def test_temperature_capabilities_info_creation() -> None:
    """Проверка создания объекта TemperatureCapabilitiesInfo."""
    temp_info = TemperatureCapabilitiesInfo(
        cpu_sensor_available=True,
        gpu_sensor_available=False
    )
    
    assert temp_info.cpu_sensor_available is True
    assert temp_info.gpu_sensor_available is False


def test_temperature_capabilities_info_repr() -> None:
    """Проверка строкового представления TemperatureCapabilitiesInfo."""
    temp_info = TemperatureCapabilitiesInfo(
        cpu_sensor_available=True,
        gpu_sensor_available=False
    )
    
    repr_str = repr(temp_info)
    assert "TemperatureCapabilitiesInfo" in repr_str
    assert "cpu_sensor_available=True" in repr_str
    assert "gpu_sensor_available=False" in repr_str
