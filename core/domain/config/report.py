# core/domain/config/report.py

import logging
from pathlib import Path
from dataclasses import dataclass

from core.domain.config.base import BaseConfig


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ReportConfig(BaseConfig):
    """
    Configuration for benchmark result persistence and formatting.

    Defines where and how the benchmark metrics should be saved after
    execution completes.

    Attributes:
        directory (Path): Target directory path for saving report files.
        formats (tuple[str, ...]): Output file formats (e.g., 'csv', 'json', 'markdown').
        use_timestamp (bool): If True, appends a timestamp to the output directory/file names.

    Note:
        - The target directory will be created automatically if it does not exist.
        - Supported formats are validated by the reporter orchestration layer.
    """
    directory: Path
    formats: tuple[str, ...]
    use_timestamp: bool