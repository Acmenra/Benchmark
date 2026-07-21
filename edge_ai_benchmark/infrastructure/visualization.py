"""Статические графики результатов бенчмарка на matplotlib (PNG для отчётов/презентаций)."""

from __future__ import annotations

import logging
from pathlib import Path

from edge_ai_benchmark.core.entities import BenchmarkResult
from edge_ai_benchmark.infrastructure.reporters._serialize import result_to_flat_dict

logger = logging.getLogger(__name__)

try:
    import matplotlib

    matplotlib.use("Agg")  # без GUI-бэкенда — безопасно для серверов/CI
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


def _require_matplotlib() -> None:
    if plt is None:
        raise RuntimeError(
            "matplotlib не установлен — установите его, чтобы строить графики "
            "(`pip install matplotlib`)"
        )


def plot_fps_comparison(results: list[BenchmarkResult], output_path: str) -> None:
    """Построить bar chart сравнения FPS по всем комбинациям модель×формат.

    Args:
        results: Результаты бенчмарка.
        output_path: Путь к выходному PNG-файлу.
    """
    _require_matplotlib()
    rows = [result_to_flat_dict(r) for r in results]
    labels = [f"{r['model']}\n{r['format']}" for r in rows]
    values = [r["fps"] for r in rows]

    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 1.2), 5))
    ax.bar(labels, values, color="#4C72B0")
    ax.set_ylabel("FPS")
    ax.set_title("Сравнение FPS по моделям и форматам")
    fig.tight_layout()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("График FPS сохранён: %s", output_path)


def plot_latency_percentiles(results: list[BenchmarkResult], output_path: str) -> None:
    """Построить grouped bar chart перцентилей latency (p50/p95/p99).

    Args:
        results: Результаты бенчмарка.
        output_path: Путь к выходному PNG-файлу.
    """
    _require_matplotlib()
    import numpy as np

    rows = [result_to_flat_dict(r) for r in results]
    labels = [f"{r['model']}\n{r['format']}" for r in rows]
    x = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 1.5), 5))
    for offset, (key, name) in enumerate(
        [("latency_p50_ms", "p50"), ("latency_p95_ms", "p95"), ("latency_p99_ms", "p99")]
    ):
        ax.bar(x + (offset - 1) * width, [r[key] for r in rows], width, label=name)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Перцентили end-to-end latency")
    ax.legend()
    fig.tight_layout()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("График latency сохранён: %s", output_path)


def plot_heatmap(results: list[BenchmarkResult], output_path: str) -> None:
    """Построить heatmap FPS по осям (модель × формат).

    Args:
        results: Результаты бенчмарка.
        output_path: Путь к выходному PNG-файлу.
    """
    _require_matplotlib()
    import numpy as np

    rows = [result_to_flat_dict(r) for r in results]
    models = sorted({r["model"] for r in rows})
    formats = sorted({r["format"] for r in rows})

    matrix = np.full((len(models), len(formats)), np.nan)
    for r in rows:
        matrix[models.index(r["model"]), formats.index(r["format"])] = r["fps"]

    fig, ax = plt.subplots(figsize=(max(4, len(formats) * 1.5), max(3, len(models) * 0.8)))
    im = ax.imshow(matrix, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(formats)))
    ax.set_xticklabels(formats)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models)
    ax.set_title("FPS heatmap: модель × формат")
    fig.colorbar(im, ax=ax, label="FPS")
    fig.tight_layout()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("Heatmap сохранён: %s", output_path)
