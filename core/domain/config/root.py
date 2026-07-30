# core/domain/config/root.py

import logging
from typing import Any
from dataclasses import dataclass

from core.domain.config.base import BaseConfig
from core.domain.config.report import ReportConfig
from core.domain.config.system import SystemInfoConfig
from core.domain.config.benchmark import BenchmarkConfig


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class Config(BaseConfig):
    """
    Root configuration object aggregating all application domains.

    This is the top-level configuration container parsed from the YAML file.
    It orchestrates the benchmark execution, system monitoring, and result
    reporting by holding references to their respective domain configurations.

    Attributes:
        benchmark (BenchmarkConfig | None): Core benchmark execution parameters.
        system_info (SystemInfoConfig | None): Hardware monitoring and telemetry settings.
        output (ReportConfig): Result persistence and formatting configuration.

    Note:
        - `benchmark` and `system_info` are optional to allow partial configurations
          (e.g., running only system info collection without a full benchmark).
        - `output` is mandatory as every execution must define where results go.
    """
    benchmark: BenchmarkConfig | None
    system_info: SystemInfoConfig | None
    output: ReportConfig