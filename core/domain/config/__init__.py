# core/domain/config/__init__.py

import logging

from core.domain.config.root import Config
from core.domain.config.base import BaseConfig
from core.domain.config.model import ModelConfig
from core.domain.config.report import ReportConfig
from core.domain.config.system import SystemInfoConfig
from core.domain.config.benchmark import BenchmarkCase, BenchmarkConfig


logger = logging.getLogger(__name__)


__all__ = [
    'Config',
    'SystemInfoConfig',
    'BaseConfig',
    'BenchmarkCase',
    'BenchmarkConfig',
    'ModelConfig',
    'ReportConfig'
]


__version__ = "0.0.0.1"