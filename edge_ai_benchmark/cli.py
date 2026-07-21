"""Тонкий CLI-слой: парсит аргументы и делегирует работу application/infrastructure.

Команды (см. README):
    python -m edge_ai_benchmark run [--config PATH] [--model NAME] [--format FMT]
    python -m edge_ai_benchmark sysinfo [--output PATH]
    python -m edge_ai_benchmark export --format {json,csv,markdown,html} --output PATH --input PATH
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from edge_ai_benchmark.application.benchmark_runner import run_benchmark
from edge_ai_benchmark.core.entities import (
    AccuracyResult,
    BenchmarkResult,
    HardwareUsageResult,
    LatencyStats,
    PerformanceResult,
    PowerResult,
)
from edge_ai_benchmark.core.enums import ModelFormat, ReportFormat
from edge_ai_benchmark.infrastructure.config_loader import ConfigError, load_config
from edge_ai_benchmark.infrastructure.models.resolver import cleanup_builtin_artifacts
from edge_ai_benchmark.infrastructure.reporters.csv_reporter import CSVReporter
from edge_ai_benchmark.infrastructure.reporters.html_reporter import HTMLReporter
from edge_ai_benchmark.infrastructure.reporters.json_reporter import JSONReporter
from edge_ai_benchmark.infrastructure.reporters.markdown_reporter import MarkdownReporter
from edge_ai_benchmark.infrastructure.system_info import collect_system_info

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = Path(__file__).parent / "configs" / "default.yaml"

_REPORTER_CLASSES = {
    ReportFormat.JSON: JSONReporter,
    ReportFormat.CSV: CSVReporter,
    ReportFormat.MARKDOWN: MarkdownReporter,
    ReportFormat.HTML: HTMLReporter,
}

_REPORTER_EXTENSIONS = {
    ReportFormat.JSON: "json",
    ReportFormat.CSV: "csv",
    ReportFormat.MARKDOWN: "md",
    ReportFormat.HTML: "html",
}


_LOG_FORMAT = "[%(asctime)s] #%(levelname)-8s %(name)s - %(message)s"


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format=_LOG_FORMAT)


def _attach_run_log_file(output_dir: Path, run_id: str) -> Path:
    """Добавить файловый обработчик логов для одного прогона `run`.

    Args:
        output_dir: Директория результатов — логи пишутся в её поддиректорию `logs/`.
        run_id: Идентификатор текущего прогона (тот же, что в имени файла
            результатов и в `runs/<task>/<run_id>/`).

    Returns:
        Путь к созданному файлу лога.
    """
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"run_{run_id}.log"

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logging.getLogger().addHandler(handler)
    return log_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="edge_ai_benchmark")
    parser.add_argument("-v", "--verbose", action="store_true", help="Включить DEBUG-логи")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Прогнать бенчмарк по конфигурации")
    run_parser.add_argument("--config", default=str(_DEFAULT_CONFIG), help="Путь к YAML-конфигу")
    run_parser.add_argument("--model", help="Фильтр по имени модели, напр. yolov8n")
    run_parser.add_argument(
        "--format", choices=[f.value for f in ModelFormat], help="Фильтр по формату"
    )

    sysinfo_parser = subparsers.add_parser("sysinfo", help="Только сбор системной информации")
    sysinfo_parser.add_argument("--output", help="Путь для сохранения JSON (иначе — stdout)")

    export_parser = subparsers.add_parser("export", help="Экспортировать результаты в формат")
    export_parser.add_argument("--format", required=True, choices=[f.value for f in ReportFormat])
    export_parser.add_argument("--output", required=True, help="Путь к выходному файлу")
    export_parser.add_argument(
        "--input", required=True, help="Путь к ранее сохранённому JSON-отчёту"
    )

    clear_parser = subparsers.add_parser(
        "clear-results", help="Удалить накопленные results/ и runs/ (ultralytics)"
    )
    clear_parser.add_argument(
        "--config", default=str(_DEFAULT_CONFIG), help="Путь к конфигу (узнать output.directory)"
    )

    return parser


def _unique_path(path: Path) -> Path:
    """Гарантировать, что путь не существует, добавляя `_1`, `_2`, ... при коллизии.

    Args:
        path: Желаемый путь к файлу.

    Returns:
        `path`, если он свободен, иначе первый свободный `path_N` с тем же расширением.
    """
    if not path.exists():
        return path
    for n in itertools.count(1):
        candidate = path.with_name(f"{path.stem}_{n}{path.suffix}")
        if not candidate.exists():
            return candidate


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except (ConfigError, FileNotFoundError) as exc:
        logger.error("Ошибка конфигурации: %s", exc)
        return 1

    run_id = f"{datetime.now():%Y%m%dT%H%M%S}"

    output_dir = Path(config.output.directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = _attach_run_log_file(output_dir, run_id)
    logger.info("Логи этого прогона сохраняются в %s", log_path)

    if args.model:
        for group in config.benchmark.models:
            group.sizes = [s for s in group.sizes if f"{group.family}{s}" == args.model]
        config.benchmark.models = [g for g in config.benchmark.models if g.sizes]
        if not config.benchmark.models:
            logger.error("Модель '%s' не найдена в конфигурации", args.model)
            return 1

    if args.format:
        config.benchmark.formats = [f for f in config.benchmark.formats if f.value == args.format]
        if not config.benchmark.formats:
            logger.error("Формат '%s' отсутствует в конфигурации", args.format)
            return 1

    predictions_root = None
    if config.benchmark.save_predictions:
        predictions_root = Path(
            config.benchmark.predictions_dir or str(output_dir / "predictions" / run_id)
        )

    specs = config.model_combinations()
    results = run_benchmark(config, run_id, predictions_root)
    if not results:
        logger.warning("Ни одна комбинация модель×формат не была успешно прогнана")

    system_info = collect_system_info(
        collect_cpu=config.system_info.collect_cpu,
        collect_ram=config.system_info.collect_ram,
        collect_disk=config.system_info.collect_disk,
        collect_gpu=config.system_info.collect_gpu,
        disk_path=config.output.directory,
    )

    suffix = f"_{run_id}" if config.output.timestamp else ""

    for fmt_name in config.output.formats:
        try:
            report_format = ReportFormat(fmt_name)
        except ValueError:
            logger.warning("Неизвестный формат отчёта в конфиге: %s", fmt_name)
            continue
        ext = _REPORTER_EXTENSIONS[report_format]
        # Никогда не перезаписываем результаты прошлых прогонов — при коллизии
        # (timestamp: false или два запуска в одну секунду) добавляем _1, _2, ...
        path = _unique_path(output_dir / f"results{suffix}.{ext}")
        try:
            _REPORTER_CLASSES[report_format]().write(results, system_info, str(path))
            # run_id всегда логируется рядом с путём — при output.timestamp:
            # false имя файла результатов его не несёт (см. `suffix` выше), а
            # без этой строки runs/<task>/<run_id>/ было бы нечем сопоставить
            # с конкретным файлом результатов.
            logger.info("Результаты (run_id=%s) записаны: %s", run_id, path)
        except RuntimeError as exc:
            logger.warning("Не удалось сформировать %s-отчёт: %s", fmt_name, exc)

    logger.info("Удаляю скачанные/экспортированные веса моделей этого прогона...")
    cleanup_builtin_artifacts(specs)

    return 0


def _cmd_sysinfo(args: argparse.Namespace) -> int:
    info = collect_system_info()
    payload = json.dumps(info, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(payload, encoding="utf-8")
        logger.info("Системная информация сохранена: %s", args.output)
    else:
        print(payload)
    return 0


def _result_from_dict(raw: dict) -> BenchmarkResult:
    accuracy = None
    if raw.get("map50") is not None or raw.get("map50_95") is not None:
        accuracy = AccuracyResult(
            precision=raw.get("precision"),
            recall=raw.get("recall"),
            map50=raw.get("map50"),
            map50_95=raw.get("map50_95"),
            mask_map50=raw.get("mask_map50"),
            mask_map50_95=raw.get("mask_map50_95"),
        )
    return BenchmarkResult(
        model=raw["model"],
        format=ModelFormat(raw["format"]),
        performance=PerformanceResult(
            fps=raw["fps"],
            compute_latency=LatencyStats(
                p50_ms=raw.get("compute_latency_p50_ms", raw["latency_p50_ms"]),
                p95_ms=raw.get("compute_latency_p95_ms", raw["latency_p95_ms"]),
                p99_ms=raw.get("compute_latency_p99_ms", raw["latency_p99_ms"]),
            ),
            end_to_end_latency=LatencyStats(
                p50_ms=raw["latency_p50_ms"],
                p95_ms=raw["latency_p95_ms"],
                p99_ms=raw["latency_p99_ms"],
            ),
        ),
        hardware=HardwareUsageResult(
            cpu_percent=raw.get("cpu_percent"),
            ram_used_mb=raw.get("ram_used_mb"),
            disk_read_mb=raw.get("disk_read_mb"),
            disk_write_mb=raw.get("disk_write_mb"),
            gpu_utilization_pct=raw.get("gpu_utilization_pct"),
            vram_usage_peak_mb=raw.get("vram_usage_peak_mb"),
        ),
        power=PowerResult(
            power_w=raw.get("power_w"),
            gpu_temperature_c=raw.get("gpu_temperature_c"),
            cpu_temperature_c=raw.get("cpu_temperature_c"),
            unsupported=raw.get("power_w") is None,
        ),
        accuracy=accuracy,
        task=raw.get("task", "detect"),
    )


def _cmd_export(args: argparse.Namespace) -> int:
    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    results = [_result_from_dict(entry) for entry in raw.get("benchmarks", [])]
    system_info = raw.get("system_info", {})

    report_format = ReportFormat(args.format)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    _REPORTER_CLASSES[report_format]().write(results, system_info, args.output)
    logger.info("Экспортировано в %s: %s", args.format, args.output)
    return 0


_WEIGHT_GLOBS = ("*.pt", "*.onnx", "*.engine", "*_openvino_model")


def _cmd_clear_results(args: argparse.Namespace) -> int:
    import shutil

    try:
        config = load_config(args.config)
        results_dir = Path(config.output.directory)
    except (ConfigError, FileNotFoundError):
        results_dir = Path("./results")

    for directory in (results_dir, Path("./runs"), Path("./.model_cache")):
        if directory.exists():
            shutil.rmtree(directory)
            logger.info("Удалено: %s", directory)
        else:
            logger.info("Уже отсутствует: %s", directory)

    # На случай прерванного прогона (cleanup_builtin_artifacts не успел
    # отработать) или вручную оставленного кэша — чистим и сами веса/экспорты.
    cwd = Path(".")
    for pattern in _WEIGHT_GLOBS:
        for path in cwd.glob(pattern):
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                logger.info("Удалено: %s", path)
            except OSError:
                logger.warning("Не удалось удалить %s", path, exc_info=True)

    return 0


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI.

    Args:
        argv: Аргументы командной строки (по умолчанию — `sys.argv[1:]`).

    Returns:
        Код завершения процесса (0 — успех).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    if args.command == "run":
        return _cmd_run(args)
    if args.command == "sysinfo":
        return _cmd_sysinfo(args)
    if args.command == "export":
        return _cmd_export(args)
    if args.command == "clear-results":
        return _cmd_clear_results(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
