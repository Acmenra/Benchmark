"""Экспорт результатов бенчмарка в интерактивный HTML-дашборд (plotly)."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from edge_ai_benchmark.core.entities import BenchmarkResult
from edge_ai_benchmark.core.interfaces import Reporter
from edge_ai_benchmark.infrastructure.reporters._serialize import result_to_flat_dict

logger = logging.getLogger(__name__)

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    go = None
    make_subplots = None

# (заголовок колонки, ключ в result_to_flat_dict, единица измерения)
_TABLE_COLUMNS = [
    ("Модель", "model", ""),
    ("Формат", "format", ""),
    ("Задача", "task", ""),
    ("FPS", "fps", "кадр/с"),
    ("Latency p50", "latency_p50_ms", "мс"),
    ("Latency p95", "latency_p95_ms", "мс"),
    ("Latency p99", "latency_p99_ms", "мс"),
    ("GPU Util", "gpu_utilization_pct", "%"),
    ("VRAM Peak", "vram_usage_peak_mb", "МБ"),
    ("CPU", "cpu_percent", "%"),
    ("RAM", "ram_used_mb", "МБ"),
    ("Power", "power_w", "Вт"),
    ("FPS/Watt", "fps_per_watt", "кадр/с/Вт"),
    ("mAP50", "map50", ""),
    ("mAP50-95", "map50_95", ""),
]


class HTMLReporter(Reporter):
    """Интерактивный HTML-дашборд: сводная таблица метрик + графики по каждой из них.

    Требует опциональную зависимость `plotly`.
    """

    def write(
        self,
        results: list[BenchmarkResult],
        system_info: dict[str, Any],
        path: str,
    ) -> None:
        if go is None:
            raise RuntimeError(
                "plotly не установлен — установите его, чтобы генерировать HTML-дашборд "
                "(`pip install edge_ai_benchmark[html]`)"
            )
        rows = [result_to_flat_dict(r) for r in results]
        labels = [f"{r['model']} / {r['format']}" for r in rows]

        fig = make_subplots(
            rows=4,
            cols=2,
            specs=[
                [{"type": "table", "colspan": 2}, None],
                [{"type": "xy"}, {"type": "xy"}],
                [{"type": "xy"}, {"type": "xy"}],
                [{"type": "xy"}, {"type": "xy"}],
            ],
            row_heights=[0.32, 0.227, 0.227, 0.226],
            vertical_spacing=0.08,
            subplot_titles=(
                "Сводная таблица по всем прогонам",
                "FPS — кадров в секунду (выше = лучше)",
                "Latency — задержка одного кадра, мс (ниже = лучше)",
                "Энергоэффективность — FPS на ватт мощности (выше = лучше)",
                "Точность детекции — mAP (выше = лучше)",
                "Загрузка GPU (%) и пиковая VRAM (МБ)",
                "Загрузка CPU (%) и используемая RAM (МБ)",
            ),
        )

        self._add_summary_table(fig, rows)
        self._add_fps_chart(fig, labels, rows)
        self._add_latency_chart(fig, labels, rows)
        self._add_efficiency_chart(fig, labels, rows)
        self._add_accuracy_chart(fig, labels, rows)
        self._add_gpu_chart(fig, labels, rows)
        self._add_cpu_ram_chart(fig, labels, rows)

        fig.update_layout(
            title=f"Edge AI Benchmark — платформа: {system_info.get('platform', 'unknown')} "
            f"| CPU: {system_info.get('cpu', {}).get('model', 'н/д')} "
            f"| сформировано {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            showlegend=True,
            height=1400,
            barmode="group",
        )

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(path)
        logger.info("HTML-дашборд записан: %s", path)

    @staticmethod
    def _add_summary_table(fig: Any, rows: list[dict[str, Any]]) -> None:
        headers = [f"{name} ({unit})" if unit else name for name, _, unit in _TABLE_COLUMNS]
        columns = [[row.get(key, "—") for row in rows] for _, key, _ in _TABLE_COLUMNS]
        fig.add_trace(
            go.Table(
                header=dict(values=headers, fill_color="#4C72B0", font=dict(color="white")),
                cells=dict(values=columns),
            ),
            row=1,
            col=1,
        )

    @staticmethod
    def _add_fps_chart(fig: Any, labels: list[str], rows: list[dict[str, Any]]) -> None:
        fig.add_trace(
            go.Bar(
                x=labels,
                y=[r["fps"] for r in rows],
                name="FPS",
                hovertemplate="%{x}<br>FPS: %{y:.1f} кадр/с<extra></extra>",
            ),
            row=2,
            col=1,
        )
        fig.update_yaxes(title_text="Кадров в секунду", row=2, col=1)

    @staticmethod
    def _add_latency_chart(fig: Any, labels: list[str], rows: list[dict[str, Any]]) -> None:
        for key, name in (
            ("latency_p50_ms", "p50 (медиана)"),
            ("latency_p95_ms", "p95"),
            ("latency_p99_ms", "p99 (худший случай)"),
        ):
            fig.add_trace(
                go.Bar(
                    x=labels,
                    y=[r[key] for r in rows],
                    name=name,
                    hovertemplate=f"%{{x}}<br>{name}: " + "%{y:.2f} мс<extra></extra>",
                ),
                row=2,
                col=2,
            )
        fig.update_yaxes(title_text="Миллисекунды", row=2, col=2)

    @staticmethod
    def _add_efficiency_chart(fig: Any, labels: list[str], rows: list[dict[str, Any]]) -> None:
        fig.add_trace(
            go.Bar(
                x=labels,
                y=[r.get("fps_per_watt") for r in rows],
                name="FPS/Watt",
                hovertemplate="%{x}<br>%{y:.2f} кадр/с на ватт<extra></extra>",
            ),
            row=3,
            col=1,
        )
        fig.update_yaxes(title_text="Кадров в секунду на ватт", row=3, col=1)

    @staticmethod
    def _add_accuracy_chart(fig: Any, labels: list[str], rows: list[dict[str, Any]]) -> None:
        for key, name in (("map50", "mAP50"), ("map50_95", "mAP50-95")):
            fig.add_trace(
                go.Bar(
                    x=labels,
                    y=[r.get(key) for r in rows],
                    name=name,
                    hovertemplate=f"%{{x}}<br>{name}: " + "%{y:.3f}<extra></extra>",
                ),
                row=3,
                col=2,
            )
        fig.update_yaxes(title_text="mAP (0-1)", row=3, col=2)

    @staticmethod
    def _add_gpu_chart(fig: Any, labels: list[str], rows: list[dict[str, Any]]) -> None:
        fig.add_trace(
            go.Bar(
                x=labels,
                y=[r.get("gpu_utilization_pct") for r in rows],
                name="GPU Util (%)",
                hovertemplate="%{x}<br>Загрузка GPU: %{y:.1f}%<extra></extra>",
            ),
            row=4,
            col=1,
        )
        fig.add_trace(
            go.Bar(
                x=labels,
                y=[r.get("vram_usage_peak_mb") for r in rows],
                name="VRAM Peak (МБ)",
                hovertemplate="%{x}<br>Пиковая VRAM: %{y:.0f} МБ<extra></extra>",
            ),
            row=4,
            col=1,
        )
        fig.update_yaxes(title_text="% / МБ", row=4, col=1)

    @staticmethod
    def _add_cpu_ram_chart(fig: Any, labels: list[str], rows: list[dict[str, Any]]) -> None:
        fig.add_trace(
            go.Bar(
                x=labels,
                y=[r.get("cpu_percent") for r in rows],
                name="CPU (%)",
                hovertemplate="%{x}<br>Загрузка CPU: %{y:.1f}%<extra></extra>",
            ),
            row=4,
            col=2,
        )
        fig.add_trace(
            go.Bar(
                x=labels,
                y=[r.get("ram_used_mb") for r in rows],
                name="RAM (МБ)",
                hovertemplate="%{x}<br>RAM: %{y:.0f} МБ<extra></extra>",
            ),
            row=4,
            col=2,
        )
        fig.update_yaxes(title_text="% / МБ", row=4, col=2)
