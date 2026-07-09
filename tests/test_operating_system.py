from infrastructure.hardware.collectors.operating_system import _empty_to_none, collect_os
from core.entities.hardware import OSInfo


def test_collect_os_returns_os_info() -> None:
    """collect_os должен возвращать заполненный OSInfo."""
    os_info = collect_os()

    assert isinstance(os_info, OSInfo)
    assert os_info.system is not None
    assert os_info.release is not None
    assert os_info.kernel is not None
    assert os_info.architecture is not None


def test_empty_to_none_converts_empty_string() -> None:
    """Пустые строки должны превращаться в None."""
    assert _empty_to_none("") is None
    assert _empty_to_none("   ") is None
    assert _empty_to_none("Darwin") == "Darwin"
