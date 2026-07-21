"""Экспорт результатов бенчмарка в JSON."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from edge_ai_benchmark.core.entities import BenchmarkResult
from edge_ai_benchmark.core.interfaces import Reporter
from edge_ai_benchmark.infrastructure.reporters._serialize import result_to_flat_dict

logger = logging.getLogger(__name__)


class JSONReporter(Reporter):
    """Записывает результаты в машиночитаемый JSON (см. пример в README)."""

    def write(
        self,
        results: list[BenchmarkResult],
        system_info: dict[str, Any],
        path: str,
    ) -> None:
        payload = {
            "timestamp": datetime.now().isoformat(),
            "system_info": system_info,
            "benchmarks": [result_to_flat_dict(r) for r in results],
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        logger.info("JSON-отчёт записан: %s", path)
