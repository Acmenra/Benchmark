# core/domain/config/system.py

import logging
from dataclasses import dataclass

from core.domain.config.base import BaseConfig


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class SystemInfoConfig(BaseConfig):
    """Конфигурация сбора системной информации во время бенчмарка."""
    collect_gpu: bool
    collect_power: bool
    collect_temperature: bool