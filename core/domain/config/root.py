import logging
from typing import Any
from dataclasses import dataclass

from core.domain.config.base import BaseConfig
from core.domain.config.benchmark import BenchmarkConfig
from core.domain.config.system import SystemInfoConfig
from core.domain.config.report import ReportConfig


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class Config(BaseConfig):
    """Корневая конфигурация приложения, объединяющая все разделы."""
    benchmark: BenchmarkConfig | None
    system_info: SystemInfoConfig | None
    output: ReportConfig