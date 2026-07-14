# tests/test_cpu.py

import logging

logger = logging.getLogger(__name__)

from hardware.collectors.cpu import (
    _empty_to_none,
    _is_cpu_name_line,
    collect_cpu,
)
from hardware.entities import CPUInfo


def test_collect_cpu_returns_cpu_info() -> None:
    """collect_cpu должен возвращать базовую информацию о процессоре."""
    cpu_info = collect_cpu()

    assert isinstance(cpu_info, CPUInfo)
    assert cpu_info.architecture is not None
    assert cpu_info.logical_cores is None or cpu_info.logical_cores > 0
    assert cpu_info.physical_cores is None or cpu_info.physical_cores > 0
    assert cpu_info.max_frequency_mhz is None or cpu_info.max_frequency_mhz > 0


def test_empty_to_none_converts_empty_string() -> None:
    """Пустые строки должны превращаться в None."""
    assert _empty_to_none("") is None
    assert _empty_to_none("   ") is None
    assert _empty_to_none("Apple") == "Apple"


def test_is_cpu_name_line_detects_linux_cpu_fields() -> None:
    """Строки с именем CPU из /proc/cpuinfo должны распознаваться."""
    assert _is_cpu_name_line("model name : Intel(R) Core(TM)")
    assert _is_cpu_name_line("Hardware : BCM2712")
    assert _is_cpu_name_line("Model : Raspberry Pi 5 Model B")
    assert _is_cpu_name_line("Processor : ARMv8 Processor")
    assert not _is_cpu_name_line("processor : 0")
    assert not _is_cpu_name_line("BogoMIPS : 108.00")
