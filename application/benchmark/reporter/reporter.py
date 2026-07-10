from typing import List, Dict, Any
from .base import BaseReporter


class Reporter:
    """Оркестратор формирования отчетов.

    Управляет вызовами конкретных реализаций BaseReporter.
    """

    def __init__(self, reporters: Dict[str, BaseReporter], enabled_formats: List[str]) -> None:
        self._reporters = reporters
        self._enabled_formats = [fmt.lower().strip() for fmt in enabled_formats]

    def report(self, entity: Any) -> None:
        """Отправить сущность во все выбранные форматы отчетов."""
        for fmt in self._enabled_formats:
            reporter = self._reporters.get(fmt)
            if not reporter:
                raise ValueError(
                    f"Unsupported report format: '{fmt}'. "
                    f"Available formats are: {list(self._reporters.keys())}"
                )
            reporter.report(entity)