"""Оркестратор бенчмарка: конфиг -> загрузчики -> метрики -> результаты.

"Дирижёр" слоя application: не содержит собственной логики измерений/загрузки
(это в infrastructure) и не описывает форму данных (это в core) — только
решает, в каком порядке и с какими параметрами вызывать infrastructure,
опираясь на `AppConfig`.
"""

from __future__ import annotations

import glob
import logging
import time
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from edge_ai_benchmark.core.entities import (
    AppConfig,
    BenchmarkConfig,
    BenchmarkResult,
    ModelSpec,
    PowerResult,
)
from edge_ai_benchmark.core.enums import ModelFormat, Precision
from edge_ai_benchmark.core.interfaces import ModelLoader
from edge_ai_benchmark.core.services.performance import build_performance_result
from edge_ai_benchmark.infrastructure import power as power_module
from edge_ai_benchmark.infrastructure.hardware_monitor import ResourceMonitor
from edge_ai_benchmark.infrastructure.models.onnx_loader import ONNXLoader
from edge_ai_benchmark.infrastructure.models.openvino_loader import OpenVINOLoader
from edge_ai_benchmark.infrastructure.models.pytorch_loader import PyTorchLoader
from edge_ai_benchmark.infrastructure.models.tensorrt_loader import TensorRTLoader

logger = logging.getLogger(__name__)

_LOADER_CLASSES: dict[ModelFormat, type[ModelLoader]] = {
    ModelFormat.PYTORCH: PyTorchLoader,
    ModelFormat.ONNX: ONNXLoader,
    ModelFormat.TENSORRT: TensorRTLoader,
    ModelFormat.OPENVINO: OpenVINOLoader,
}

_IMAGE_EXTENSIONS = ("*.jpg", "*.jpeg", "*.png", "*.bmp")


def _release_gpu_memory() -> None:
    """Освободить кэшированную CUDA-память между прогонами.

    Без этого VRAM-метрики (`ResourceMonitor.vram_usage_peak_mb`, через
    `pynvml`) следующей модели "затекают" остатками от предыдущей — PyTorch
    держит кэширующий аллокатор и не возвращает память ОС сам по себе.
    """
    import gc

    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except ImportError:
        pass


def load_test_images(directory: str | Path | None, task: str = "detect") -> list[np.ndarray]:
    """Загрузить тестовые кадры: фото и/или видео из директории.

    `directory` — директория (можно положить туда и фото, и несколько
    видеофайлов сразу — все будут использованы); либо, для удобства, путь
    напрямую к одному видеофайлу.

    Порядок разрешения:
    1. Если `directory` не задан — берётся завезённая в репозиторий
       директория с реальными фото под `task` (см.
       `infrastructure.dataset.default_test_images_dir`), работает офлайн.
    2. Если `directory` указывает на один видеофайл — декодировать кадры из
       него (см. `infrastructure.video`).
    3. Иначе — фото (`*.jpg/*.png/...`) и видео (`*.mp4/*.avi/...`) из
       директории `directory`, объединённые в один список кадров.
    4. Если ничего не найдено — один синтетический кадр с предупреждением.

    Args:
        directory: Директория с фото/видео, путь к одному видеофайлу
            (`benchmark.test_images` в конфиге), либо `None` для дефолтной
            завезённой директории под `task`.
        task: ``"detect"`` или ``"segment"`` — только для выбора дефолтной
            директории, когда `directory` не задан.

    Returns:
        Список кадров BGR/HWC.
    """
    from edge_ai_benchmark.infrastructure.dataset import default_test_images_dir
    from edge_ai_benchmark.infrastructure.video import (
        is_video_file,
        load_video_frames,
        load_video_frames_from_directory,
    )

    if directory is None:
        directory = default_test_images_dir(task)

    if is_video_file(directory):
        frames = load_video_frames(directory)
        if frames:
            return frames
        logger.warning("Видео '%s' не дало кадров", directory)

    paths: list[str] = []
    for pattern in _IMAGE_EXTENSIONS:
        paths.extend(glob.glob(str(Path(directory) / pattern)))

    images = [img for p in sorted(paths) if (img := cv2.imread(p)) is not None]
    images.extend(load_video_frames_from_directory(directory))
    if images:
        return images

    logger.warning(
        "В '%s' не найдено тестовых изображений — использую синтетический кадр, "
        "результаты FPS/latency не отражают реальную нагрузку",
        directory,
    )
    return [np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)]


def _resolve_measurement_dataset(bench_cfg: BenchmarkConfig, purpose: str) -> str | None:
    """Собрать датасет ultralytics из `test_images` для accuracy/калибровки INT8.

    Один и тот же источник (`test_images`) используется и для accuracy, и для
    калибровки INT8 — вместо отдельного скачиваемого датасета. Видео и
    директории без разметки (`labels/`) не дают датасета — вызывающий код
    должен пропустить операцию, а не подставлять посторонний датасет.

    Args:
        bench_cfg: Конфигурация бенчмарка.
        purpose: Название операции для лога (например, "оценка точности"
            или "калибровка INT8"), не влияет на логику.

    Returns:
        Путь к YAML-датасету, либо `None`, если разметки не найдено.
    """
    from edge_ai_benchmark.infrastructure.video import is_video_file

    if bench_cfg.test_images is not None and is_video_file(bench_cfg.test_images):
        logger.info(
            "%s недоступна для видео '%s' — нет размеченных кадров рядом "
            "(задайте benchmark.accuracy_dataset явно, если разметка есть)",
            purpose,
            bench_cfg.test_images,
        )
        return None

    from edge_ai_benchmark.infrastructure.dataset import (
        default_test_images_dir,
        resolve_accuracy_dataset,
    )

    images_dir = (
        Path(bench_cfg.test_images)
        if bench_cfg.test_images is not None
        else default_test_images_dir(bench_cfg.task)
    )
    dataset = resolve_accuracy_dataset(images_dir, bench_cfg.task)
    if dataset is None:
        logger.info(
            "В '%s' нет разметки (labels/) рядом с изображениями — %s недоступна",
            images_dir,
            purpose,
        )
    return dataset


def _extract_compute_ms(loader: ModelLoader, raw_result: Any, fallback_ms: float) -> float:
    """Достать "чистое" время forward pass последнего `predict()`.

    Порядок источников:
    1. ultralytics-результаты несут ``speed['inference']`` (мс) — так меряет
       PyTorchLoader, ничего своего замерять не нужно.
    2. `loader.last_compute_ms()` — остальные загрузчики (ONNX/TensorRT/
       OpenVINO) сами измеряют время вокруг вызова инференса, см. их `predict()`.
    3. `fallback_ms` (то же значение, что end-to-end) — если ни то ни другое
       недоступно, честная деградация вместо придуманного числа.
    """
    try:
        speed = raw_result[0].speed
        return float(speed["inference"])
    except (TypeError, KeyError, IndexError, AttributeError):
        pass

    compute_ms = loader.last_compute_ms()
    return compute_ms if compute_ms is not None else fallback_ms


_PROGRESS_LOG_INTERVAL_S = 10.0


def _frame_indices(bench_cfg: BenchmarkConfig, image_count: int) -> Iterator[int]:
    """Индексы кадров для одного прогона.

    Приоритет: `duration_minutes` (по времени, циклический повтор кадров) ->
    `main_iterations` (фиксированное число замеров, циклический повтор) ->
    `main_iterations is None` (каждый кадр из датасета ровно один раз, без повторов).
    """
    if bench_cfg.duration_minutes:
        deadline = time.perf_counter() + bench_cfg.duration_minutes * 60.0
        i = 0
        while time.perf_counter() < deadline:
            yield i
            i += 1
    elif bench_cfg.main_iterations is None:
        yield from range(image_count)
    else:
        yield from range(bench_cfg.main_iterations)


def _log_run_mode(spec: ModelSpec, bench_cfg: BenchmarkConfig, image_count: int) -> int | None:
    """Залогировать выбранный режим прогона и вернуть ожидаемое число кадров.

    Returns:
        Общее число кадров, либо `None` в режиме по времени (`duration_minutes`
        — там оно заранее неизвестно).
    """
    if bench_cfg.duration_minutes:
        logger.info(
            "%s [%s]: режим по времени, %.1f мин",
            spec.name,
            spec.fmt.value,
            bench_cfg.duration_minutes,
        )
        return None
    if bench_cfg.main_iterations is None:
        logger.info(
            "%s [%s]: прогон всего датасета один раз, %d кадров",
            spec.name,
            spec.fmt.value,
            image_count,
        )
        return image_count
    return bench_cfg.main_iterations


def _fmt(value: float | None, fmt: str) -> str:
    return format(value, fmt) if value is not None else "н/д"


def _log_progress(
    spec: ModelSpec,
    done: int,
    total: int | None,
    window_ms: list[float],
    monitor: ResourceMonitor,
) -> None:
    """Раз в `_PROGRESS_LOG_INTERVAL_S` секунд вывести в лог метрики за прошедшее окно.

    Args:
        spec: Текущая комбинация модель×формат.
        done: Сколько кадров уже обработано.
        total: Сколько всего кадров запланировано (`None` в режиме по времени
            `duration_minutes` — там заранее неизвестно).
        window_ms: Задержки кадров (мс) с прошлого прогресс-лога — по ним
            считаются средняя/пиковая/минимальная latency за окно.
        monitor: Активный `ResourceMonitor` — снимок средних CPU/GPU/RAM/
            питания/температуры, накопленных с начала прогона.
    """
    if not window_ms:
        return
    avg_ms = sum(window_ms) / len(window_ms)
    fps = 1000.0 / avg_ms if avg_ms > 0 else 0.0
    snap = monitor.snapshot()
    progress = f"{done}/{total}" if total is not None else str(done)
    logger.info(
        "%s [%s] %s кадров | FPS~%.1f | latency avg=%.1fмс min=%.1fмс max=%.1fмс "
        "| CPU=%s%% GPU=%s%% RAM=%sМБ Power=%sВт GPU_temp=%s°C",
        spec.name,
        spec.fmt.value,
        progress,
        fps,
        avg_ms,
        min(window_ms),
        max(window_ms),
        _fmt(snap.cpu_percent, ".0f"),
        _fmt(snap.gpu_utilization_pct, ".0f"),
        _fmt(snap.ram_used_mb, ".0f"),
        _fmt(snap.power_w, ".1f"),
        _fmt(snap.gpu_temperature_c, ".0f"),
    )


def run_single_benchmark(
    spec: ModelSpec,
    images: list[np.ndarray],
    config: AppConfig,
    run_id: str = "adhoc",
    predictions_root: Path | None = None,
) -> BenchmarkResult | None:
    """Прогнать бенчмарк для одной комбинации модель×формат.

    Args:
        spec: Комбинация модель×формат для прогона.
        images: Тестовые изображения (см. `load_test_images`).
        config: Конфигурация бенчмарка.
        run_id: Идентификатор текущего прогона `run` — используется как имя
            подпапки в `runs/<task>/<run_id>/`, чтобы диагностические
            картинки ultralytics можно было соотнести с конкретным файлом
            результатов в `results/` (см. `cli._cmd_run`).
        predictions_root: Если `config.benchmark.save_predictions` включён —
            корневая директория для аннотированных кадров (каждой комбинации
            модель×формат — своя поддиректория `<model>_<format>/`).
            Игнорируется, если `save_predictions` выключен.

    Returns:
        `BenchmarkResult`, либо `None`, если формат недоступен в этом
        окружении или загрузка модели завершилась ошибкой (в обоих случаях
        подробность пишется в логи с уровнем WARNING/ERROR, без исключения
        наружу — остальные комбинации продолжают выполняться).
    """
    loader_cls = _LOADER_CLASSES[spec.fmt]
    if not loader_cls.is_available():
        logger.warning(
            "Формат %s недоступен в этом окружении (не установлен рантайм) — пропускаю %s",
            spec.fmt.value,
            spec.name,
        )
        return None

    bench_cfg = config.benchmark
    if spec.precision is Precision.INT8 and spec.calibration_dataset is None:
        calibration_dataset = _resolve_measurement_dataset(bench_cfg, "калибровка INT8")
        if calibration_dataset is not None:
            spec = replace(spec, calibration_dataset=calibration_dataset)

    loader = loader_cls()
    try:
        loader.load(spec)
    except Exception:
        logger.error("Не удалось загрузить %s (%s)", spec.name, spec.fmt.value, exc_info=True)
        return None

    loader.warmup(bench_cfg.input_size, bench_cfg.warmup_iterations)

    monitor = ResourceMonitor()
    monitor.start()

    total_frames = _log_run_mode(spec, bench_cfg, len(images))

    predictions_dir = None
    if bench_cfg.save_predictions and predictions_root is not None:
        predictions_dir = Path(predictions_root) / f"{spec.name}_{spec.fmt.value}"
        predictions_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Аннотированные кадры %s [%s] сохраняются в %s",
            spec.name,
            spec.fmt.value,
            predictions_dir,
        )

    end_to_end_ms: list[float] = []
    compute_ms: list[float] = []
    window_ms: list[float] = []
    last_progress_log = time.perf_counter()
    done = 0

    for i in _frame_indices(bench_cfg, len(images)):
        image = images[i % len(images)]
        start = time.perf_counter()
        raw_result = loader.predict(image)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        end_to_end_ms.append(elapsed_ms)
        compute_ms.append(_extract_compute_ms(loader, raw_result, elapsed_ms))
        window_ms.append(elapsed_ms)
        done += 1

        if predictions_dir is not None:
            # Вне таймингов выше — annotate() гоняет полный ultralytics-пайплайн
            # (NMS/маски) отдельно от "сырого" predict(), не должен искажать
            # измеренные FPS/latency.
            try:
                annotated = loader.annotate(image)
                cv2.imwrite(str(predictions_dir / f"frame_{done:05d}.jpg"), annotated)
            except Exception:
                logger.warning(
                    "Не удалось сохранить аннотированный кадр %d для %s [%s]",
                    done,
                    spec.name,
                    spec.fmt.value,
                    exc_info=True,
                )

        now = time.perf_counter()
        if now - last_progress_log >= _PROGRESS_LOG_INTERVAL_S:
            _log_progress(spec, done, total_frames, window_ms, monitor)
            window_ms = []
            last_progress_log = now

    # Финальный flush: если цикл закончился раньше 10с (мало кадров/main_iterations=null),
    # прогресс-лог выше мог ни разу не сработать — печатаем итог по тому, что успели.
    if window_ms:
        _log_progress(spec, done, total_frames, window_ms, monitor)

    hardware = monitor.stop()

    power_result = PowerResult(unsupported=True)
    if config.system_info.collect_power or config.system_info.collect_temperature:
        power = (
            power_module.get_power_consumption()
            if config.system_info.collect_power
            else PowerResult(unsupported=True)
        )
        temperature = (
            power_module.get_temperature()
            if config.system_info.collect_temperature
            else PowerResult(unsupported=True)
        )
        power_result = PowerResult(
            power_w=power.power_w,
            gpu_temperature_c=temperature.gpu_temperature_c,
            cpu_temperature_c=temperature.cpu_temperature_c,
            unsupported=power.unsupported and temperature.unsupported,
        )

    accuracy = None
    if bench_cfg.measure_accuracy:
        dataset = bench_cfg.accuracy_dataset or _resolve_measurement_dataset(
            bench_cfg, "оценка точности"
        )
        if dataset is not None:
            try:
                accuracy = loader.evaluate_accuracy(dataset, bench_cfg.task, run_id)
            except NotImplementedError as exc:
                logger.info("Оценка точности недоступна для %s: %s", spec.fmt.value, exc)
            except Exception:
                logger.warning(
                    "Не удалось оценить точность %s на датасете %s",
                    spec.name,
                    dataset,
                    exc_info=True,
                )

    loader.unload()
    _release_gpu_memory()

    return BenchmarkResult(
        model=spec.name,
        format=spec.fmt,
        performance=build_performance_result(compute_ms, end_to_end_ms),
        hardware=hardware,
        power=power_result,
        accuracy=accuracy,
        task=bench_cfg.task,
    )


def run_benchmark(
    config: AppConfig,
    run_id: str = "adhoc",
    predictions_root: Path | None = None,
) -> list[BenchmarkResult]:
    """Прогнать полный бенчмарк по всем комбинациям, заданным в конфигурации.

    Args:
        config: Конфигурация бенчмарка (`AppConfig`).
        run_id: Идентификатор текущего прогона `run` (см. `run_single_benchmark`).
        predictions_root: См. `run_single_benchmark`.

    Returns:
        Список `BenchmarkResult` — по одному на каждую успешно прогнанную
        комбинацию модель×формат (недоступные форматы пропускаются с WARNING).
    """
    images = load_test_images(config.benchmark.test_images, config.benchmark.task)
    results: list[BenchmarkResult] = []
    for spec in config.model_combinations():
        logger.info("Бенчмарк %s [%s]...", spec.name, spec.fmt.value)
        result = run_single_benchmark(spec, images, config, run_id, predictions_root)
        if result is not None:
            results.append(result)
    return results
