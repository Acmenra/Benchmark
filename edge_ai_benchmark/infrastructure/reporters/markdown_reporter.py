"""Экспорт результатов бенчмарка в Markdown (для документации)."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from edge_ai_benchmark.core.entities import BenchmarkResult
from edge_ai_benchmark.core.interfaces import Reporter
from edge_ai_benchmark.infrastructure.reporters._serialize import result_to_flat_dict

logger = logging.getLogger(__name__)

_TABLE_COLUMNS = [
    ("model", "Model"),
    ("format", "Format"),
    ("task", "Task"),
    ("fps", "FPS"),
    ("latency_p50_ms", "Latency p50 (ms)"),
    ("latency_p95_ms", "Latency p95 (ms)"),
    ("latency_p99_ms", "Latency p99 (ms)"),
    ("gpu_utilization_pct", "GPU Util (%)"),
    ("vram_usage_peak_mb", "VRAM Peak (MB)"),
    ("power_w", "Power (W)"),
    ("fps_per_watt", "FPS/W"),
    ("map50_95", "mAP50-95"),
]


class MarkdownReporter(Reporter):
    """Записывает результаты в Markdown-таблицу с секцией системной информации."""

    def write(
        self,
        results: list[BenchmarkResult],
        system_info: dict[str, Any],
        path: str,
    ) -> None:
        lines = [
            "# Edge AI Benchmark — отчёт",
            "",
            f"Сформирован: {datetime.now().isoformat()}",
            "",
            "## Система",
            "",
            f"- OS: {system_info.get('os', 'unknown')}",
            f"- Python: {system_info.get('python_version', 'unknown')}",
            f"- Платформа: {system_info.get('platform', 'unknown')}",
        ]
        cpu = system_info.get("cpu")
        if cpu:
            lines.append(
                f"- CPU: {cpu.get('model')} "
                f"({cpu.get('physical_cores')} физ. / {cpu.get('logical_cores')} лог. ядер)"
            )
        gpu = system_info.get("gpu")
        if gpu and gpu.get("available"):
            lines.append(f"- GPU: {gpu.get('model')} ({gpu.get('vram_total_gb')} GB VRAM)")

        lines += ["", "## Результаты", ""]
        header = [label for _, label in _TABLE_COLUMNS]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")

        for result in results:
            flat = result_to_flat_dict(result)
            row = [str(flat.get(key, "")) for key, _ in _TABLE_COLUMNS]
            lines.append("| " + " | ".join(row) + " |")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info("Markdown-отчёт записан: %s", path)
