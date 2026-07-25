# infrastructure/hardware/collectors/operating_system.py

import logging
import platform
from core.domain.operating_system import OSInfo


logger = logging.getLogger(__name__)


def collect_os() -> OSInfo:
    """
    Сбор базовой информации об операционной системе.
    Набор полей зависит от текущего OSInfo.
    """
    return OSInfo(
        system=_empty_to_none(platform.system()),
        release=_empty_to_none(platform.release()),
        kernel=_empty_to_none(platform.version()),
        architecture=_empty_to_none(platform.machine()),
    )


def _empty_to_none(value: str) -> str | None:
    """Преобразование пустой строки в None для отчета."""
    stripped_value = value.strip()
    return stripped_value or None