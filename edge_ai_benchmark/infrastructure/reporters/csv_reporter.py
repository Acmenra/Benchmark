"""Экспорт результатов бенчмарка в CSV (для Excel/pandas)."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from edge_ai_benchmark.core.entities import BenchmarkResult
from edge_ai_benchmark.core.interfaces import Reporter
from edge_ai_benchmark.infrastructure.reporters._serialize import result_to_flat_dict

logger = logging.getLogger(__name__)


class CSVReporter(Reporter):
    """Записывает результаты в CSV — одна строка на комбинацию модель×формат."""

    def write(
        self,
        results: list[BenchmarkResult],
        system_info: dict[str, Any],
        path: str,
    ) -> None:
        rows = [result_to_flat_dict(r) for r in results]
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        if not rows:
            Path(path).write_text("", encoding="utf-8")
            logger.warning("Нет результатов для CSV-отчёта: %s", path)
            return

        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        logger.info("CSV-отчёт записан: %s", path)
