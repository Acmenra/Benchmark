# core/domain/config/report.py

import logging
from pathlib import Path
from dataclasses import dataclass

from core.domain.config.base import BaseConfig

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ReportConfig(BaseConfig):
    """Конфигурация вывода и сохранения результатов бенчмарка."""
    directory: Path
    formats: tuple[str, ...]
    use_timestamp: bool