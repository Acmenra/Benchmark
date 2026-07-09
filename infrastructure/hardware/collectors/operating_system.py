# # infrastructure/hardware/collectors/operating_system.py

import platform

from core.entities.hardware import OSInfo


def collect_os() -> OSInfo:
    """
    Сбор базовой информации об операционной системе.
    Набор полей зависит от текущего OSInfo.
    """
    return OSInfo(
        # После согласования entities.py можно добавить в OSInfo python_version
        system=_empty_to_none(platform.system()),
        release=_empty_to_none(platform.release()),
        kernel=_empty_to_none(platform.version()),
        architecture=_empty_to_none(platform.machine()),
    )


def _empty_to_none(value: str) -> str | None:
    """Преобразование пустой строки в None для отчета."""
    stripped_value = value.strip()
    return stripped_value or None