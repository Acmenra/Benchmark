# application/benchmark/reporter/reporter.py

import logging
from typing import List, Dict, Any
from application.benchmark.reporter import BaseReporter


logger = logging.getLogger(__name__)


class Reporter:
    """Оркестратор, вызывающий все включённые репортеры."""

    def __init__(self, reporters: Dict[str, BaseReporter], enabled_formats: List[str]) -> None:
        self._reporters = reporters
        self._enabled_formats = [fmt.lower().strip() for fmt in enabled_formats]

    def report(self, data: Any) -> None:
        for fmt in self._enabled_formats:
            reporter = self._reporters.get(fmt)
            if not reporter:
                raise ValueError(
                    f"Unsupported report format: '{fmt}'. "
                    f"Available formats are: {list(self._reporters.keys())}"
                )
            reporter.report(data)