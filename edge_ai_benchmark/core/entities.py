"""Сущности предметной области Edge AI Benchmark Suite.

Все датаклассы здесь — простые структуры данных ("что это"), без знания о том,
как их значения получаются (файлы, железо, сеть) — этим занимается
``infrastructure``, а решениями о том, когда и зачем их использовать —
``application``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from edge_ai_benchmark.core.enums import ModelFormat, ModelSource, Precision


@dataclass(frozen=True)
class ModelSpec:
    """Описание конкретной комбинации модель+формат для бенчмарка.

    Attributes:
        family: Семейство модели, например ``yolov8``.
        size: Размер модели, например ``n``, ``s``, ``m``, ``l``, ``x``.
        fmt: Формат весов (`ModelFormat`).
        source: Откуда берётся вес (`ModelSource`).
        local_path: Путь к локальному чекпоинту (для `ModelSource.LOCAL`).
        hf_repo_id: Идентификатор репозитория на Hugging Face Hub
            (для `ModelSource.HUGGINGFACE`), например ``"Ultralytics/YOLOv8"``.
        hf_filename: Имя файла весов внутри репозитория HF Hub.
        precision: Точность экспорта/инференса (`Precision`).
        calibration_dataset: Датасет для калибровки INT8 (только при
            `precision == Precision.INT8`, для остальных `None`).
        task: ``"detect"`` или ``"segment"`` — для `ModelSource.BUILTIN`
            определяет, берётся ли обычный чекпоинт (``yolov8n.pt``) или его
            сегментационный вариант (``yolov8n-seg.pt``), см. `resolver.builtin_asset_stem`.
        input_size: Сторона квадратного входного изображения — прокидывается
            в экспорт (`imgsz=`) для ONNX/OpenVINO/TensorRT и в `predict()`/
            `val()` для всех форматов, чтобы реально управлять разрешением
            инференса (не только размером warmup-заглушки).
    """

    family: str
    size: str
    fmt: ModelFormat
    source: ModelSource = ModelSource.BUILTIN
    local_path: str | None = None
    hf_repo_id: str | None = None
    hf_filename: str | None = None
    precision: Precision = Precision.FP32
    calibration_dataset: str | None = None
    task: str = "detect"
    input_size: int = 640

    @property
    def name(self) -> str:
        """Короткое имя модели вида ``yolov8n``."""
        return f"{self.family}{self.size}"

    def __post_init__(self) -> None:
        if self.source is ModelSource.LOCAL and not self.local_path:
            raise ValueError("ModelSpec с source=LOCAL требует local_path")
        if self.source is ModelSource.HUGGINGFACE and not (self.hf_repo_id and self.hf_filename):
            raise ValueError("ModelSpec с source=HUGGINGFACE требует hf_repo_id и hf_filename")


@dataclass
class LatencyStats:
    """Перцентили задержки одного вида замера, в миллисекундах."""

    p50_ms: float
    p95_ms: float
    p99_ms: float


@dataclass
class PerformanceResult:
    """Результат замера производительности одного прогона.

    Attributes:
        fps: Кадров в секунду, посчитано по `end_to_end_latency`.
        compute_latency: "Чистая" задержка — только forward pass модели на
            GPU/CPU (то, что было бы в realtime-стриминге при уже готовых
            в памяти устройства тензорах).
        end_to_end_latency: Полная задержка, включая передачу данных
            RAM -> устройство (H2D), препроцессинг и постпроцессинг —
            то, что реально видит потребитель кадра в стриминге.
    """

    fps: float
    compute_latency: LatencyStats
    end_to_end_latency: LatencyStats


@dataclass
class CpuCacheInfo:
    """Размеры кэшей CPU, в килобайтах (None, если недоступно на платформе)."""

    l1_kb: int | None = None
    l2_kb: int | None = None
    l3_kb: int | None = None


@dataclass
class CpuInfo:
    """Подробные характеристики CPU."""

    model: str
    architecture: str
    physical_cores: int | None = None
    logical_cores: int | None = None
    frequency_current_mhz: float | None = None
    frequency_max_mhz: float | None = None
    cache: CpuCacheInfo = field(default_factory=CpuCacheInfo)


@dataclass
class DiskInfo:
    """Характеристики диска, на котором лежат модели/результаты."""

    device: str
    filesystem: str | None
    total_gb: float
    used_gb: float
    free_gb: float


@dataclass
class HardwareUsageResult:
    """Результат замера использования ресурсов во время прогона.

    ``cpu_percent`` — суммарная загрузка CPU процессом бенчмарка;
    ``cpu_percent_per_core`` — загрузка по каждому логическому ядру отдельно.
    """

    cpu_percent: float | None = None
    cpu_percent_per_core: list[float] = field(default_factory=list)
    ram_used_mb: float | None = None
    disk_read_mb: float | None = None
    disk_write_mb: float | None = None
    gpu_utilization_pct: float | None = None
    vram_usage_peak_mb: float | None = None


@dataclass
class PowerResult:
    """Результат замера энергопотребления и температуры."""

    power_w: float | None = None
    gpu_temperature_c: float | None = None
    cpu_temperature_c: float | None = None
    unsupported: bool = False


@dataclass
class AccuracyResult:
    """Метрики качества модели (см. `Ultralytics Metrics
    <https://docs.ultralytics.com/guides/yolo-performance-metrics/>`_).

    Поля ``mask_*`` заполняются только для задач сегментации (task=segment),
    для детекции остаются ``None``.
    """

    precision: float | None = None
    recall: float | None = None
    map50: float | None = None
    map50_95: float | None = None
    mask_precision: float | None = None
    mask_recall: float | None = None
    mask_map50: float | None = None
    mask_map50_95: float | None = None


@dataclass
class BenchmarkResult:
    """Полная строка результата: одна комбинация модель×формат."""

    model: str
    format: ModelFormat
    performance: PerformanceResult
    hardware: HardwareUsageResult = field(default_factory=HardwareUsageResult)
    power: PowerResult = field(default_factory=PowerResult)
    accuracy: AccuracyResult | None = None
    task: str = "detect"
    """Задача, на которой гонялся бенчмарк: ``detect`` или ``segment`` (см.
    `BenchmarkConfig.task`) — влияет на то, какие accuracy-метрики заполнены
    (`AccuracyResult.mask_*` только при ``task == "segment"``)."""

    @property
    def fps_per_watt(self) -> float | None:
        """Энергоэффективность: кадров в секунду на ватт мощности.

        Returns:
            `fps / power_w`, либо `None`, если мощность не измерена
            (см. `PowerResult.unsupported`).
        """
        if self.power.power_w in (None, 0) or self.power.unsupported:
            return None
        return self.performance.fps / self.power.power_w


@dataclass
class ModelGroupConfig:
    """Группа размеров одного семейства моделей из конфигурации."""

    family: str
    sizes: list[str]
    source: ModelSource = ModelSource.BUILTIN
    local_paths: dict[str, str] = field(default_factory=dict)
    """Отображение size -> путь к локальному чекпоинту (для source=LOCAL)."""
    hf_repo_id: str | None = None
    hf_filenames: dict[str, str] = field(default_factory=dict)
    """Отображение size -> имя файла в HF-репозитории (для source=HUGGINGFACE)."""


@dataclass
class BenchmarkConfig:
    """Раздел ``benchmark`` конфигурации."""

    models: list[ModelGroupConfig]
    formats: list[ModelFormat]
    input_size: int = 640
    batch_size: int = 1
    warmup_iterations: int = 10
    main_iterations: int | None = None
    """Число замеров на комбинацию модель×формат, с циклическим повтором
    кадров, если их меньше. По умолчанию `None` — прогнать каждый кадр из
    `test_images` ровно один раз, без повторов (игнорируется, если задан
    `duration_minutes`). Задайте числом, чтобы зафиксировать одинаковое
    количество замеров независимо от размера датасета."""
    duration_minutes: float | None = None
    """Если задано — каждая комбинация модель×формат гоняется по времени
    (столько минут), циклически повторяя доступные кадры, вместо
    `main_iterations`. Имеет приоритет над `main_iterations`."""
    confidence_threshold: float = 0.25
    test_images: str | None = None
    """Директория с тестовыми изображениями, либо путь к видеофайлу
    (`infrastructure.video`). FPS/latency и accuracy считаются на одном и том
    же источнике. `None` (по умолчанию) — завезённые в репозиторий фото с
    разметкой под `task` (`infrastructure.dataset.default_test_images_dir`).

    Своя директория должна называться `images` и иметь рядом `labels` с
    YOLO-txt разметкой (конвенция ultralytics, `img2label_paths`) — иначе
    accuracy для неё не считается (FPS/latency считаются в любом случае).
    Для видео accuracy не считается, если явно не задан `accuracy_dataset`."""
    task: str = "detect"
    """Задача модели: ``detect`` или ``segment`` — влияет на набор accuracy-метрик."""
    accuracy_dataset: str | None = None
    """Явный путь/имя YAML датасета в формате ultralytics для оценки точности.

    Если `None` (по умолчанию) — датасет для accuracy строится автоматически
    из `test_images` (см. его докстринг); если валидной разметки рядом нет —
    accuracy просто не считается для этой комбинации."""
    measure_accuracy: bool = True
    precision: Precision = Precision.FP32
    """Точность экспорта/инференса для всех комбинаций. `FP16` — без
    калибровки, обычно безопасное ускорение. `INT8` — калибруется на
    `accuracy_dataset` (или, если не задан, на том же `test_images`, что и
    accuracy — см. `application.benchmark_runner`), заметно дольше при первом
    экспорте и заметнее теряет accuracy."""
    save_predictions: bool = False
    """Сохранять на диск каждый обработанный моделью кадр с отрисованными
    боксами/масками (как `ultralytics.engine.results.Results.plot()`) — для
    фото и для видео (каждый кадр видео сохраняется отдельной картинкой).
    Работает для любого источника `test_images` и любого формата модели."""
    predictions_dir: str | None = None
    """Куда сохранять кадры из `save_predictions`. `None` (по умолчанию) —
    `<output.directory>/predictions/<run_id>/<model>_<format>/` (см.
    `cli._cmd_run`)."""


@dataclass
class OutputConfig:
    """Раздел ``output`` конфигурации."""

    directory: str = "./results/"
    formats: list[str] = field(default_factory=lambda: ["json", "csv", "markdown"])
    timestamp: bool = True


@dataclass
class SystemInfoConfig:
    """Раздел ``system_info`` конфигурации.

    ``collect_cpu``/``collect_ram``/``collect_disk`` включены по умолчанию —
    эти данные всегда дёшево доступны через `platform`/`psutil` на любой
    платформе. ``collect_gpu``/``collect_power``/``collect_temperature``
    тоже включены по умолчанию, но могут требовать необязательных
    зависимостей (`pynvml`) или недоступного железа и в этом случае
    деградируют до `None`/``unsupported`` вместо ошибки.
    """

    collect_cpu: bool = True
    collect_ram: bool = True
    collect_disk: bool = True
    collect_gpu: bool = True
    collect_power: bool = True
    collect_temperature: bool = True


@dataclass
class AppConfig:
    """Корневая конфигурация приложения."""

    benchmark: BenchmarkConfig
    output: OutputConfig
    system_info: SystemInfoConfig

    def model_combinations(self) -> list[ModelSpec]:
        """Развернуть группы моделей и форматы в список конкретных `ModelSpec`.

        Returns:
            Список `ModelSpec` — декартово произведение (family × size) × format.
        """
        # Явный accuracy_dataset (если задан) используется и для калибровки INT8.
        # Если не задан — им же (при наличии разметки) заполнит application-слой
        # перед экспортом, см. `application.benchmark_runner`; core не решает,
        # откуда брать датасет с диска — это работа infrastructure.
        calibration_dataset = (
            self.benchmark.accuracy_dataset if self.benchmark.precision is Precision.INT8 else None
        )

        specs: list[ModelSpec] = []
        for group in self.benchmark.models:
            for size in group.sizes:
                for fmt in self.benchmark.formats:
                    if group.source is ModelSource.LOCAL:
                        specs.append(
                            ModelSpec(
                                family=group.family,
                                size=size,
                                fmt=fmt,
                                source=ModelSource.LOCAL,
                                local_path=group.local_paths.get(size),
                                precision=self.benchmark.precision,
                                calibration_dataset=calibration_dataset,
                                task=self.benchmark.task,
                                input_size=self.benchmark.input_size,
                            )
                        )
                    elif group.source is ModelSource.HUGGINGFACE:
                        specs.append(
                            ModelSpec(
                                family=group.family,
                                size=size,
                                fmt=fmt,
                                source=ModelSource.HUGGINGFACE,
                                hf_repo_id=group.hf_repo_id,
                                hf_filename=group.hf_filenames.get(size),
                                precision=self.benchmark.precision,
                                calibration_dataset=calibration_dataset,
                                task=self.benchmark.task,
                                input_size=self.benchmark.input_size,
                            )
                        )
                    else:
                        specs.append(
                            ModelSpec(
                                family=group.family,
                                size=size,
                                fmt=fmt,
                                precision=self.benchmark.precision,
                                calibration_dataset=calibration_dataset,
                                task=self.benchmark.task,
                                input_size=self.benchmark.input_size,
                            )
                        )
        return specs
