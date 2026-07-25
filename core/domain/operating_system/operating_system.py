# core/domain/operating_system/operating_system.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class OSInfo:
    """Информация об операционной системе.

    Attributes:
        system (str | None): Название операционной системы.
        release (str | None): Версия выпуска операционной системы.
        kernel (str | None): Версия ядра операционной системы.
        architecture (str | None): Архитектура системы.
    """

    system: str | None
    release: str | None
    kernel: str | None
    architecture: str | None