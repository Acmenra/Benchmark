# core/enums/model.py

import logging
from enum import Enum
from uuid import UUID

from acmenra_cv import (
    DeviceType as _DeviceType, 
    TaskType as _TaskType
)

logger = logging.getLogger(__name__)


TaskType = _TaskType 


DeviceType = _DeviceType




class ExportTarget(Enum):
    X86_64 = 'x86_64'
    ARM64 = 'arm64'
    RISC_V = 'risc_v'  # для будущих edge-чипов

# reporter.py
class ReportFormat(Enum):
    JSON = 'json'
    CSV = 'csv'
    MARKDOWN = 'markdown'
    HTML = 'html'

class QuantizationLevel(Enum):
    FP64 = 'fp64'   # Двойная точность, нет оптимизации
    FP32 = 'fp32'   # Полная точность, нет оптимизации
    FP16 = 'fp16'   # Половинная точность, 2× ускорение на GPU
    INT8 = 'int8'   # 8-битное квантование, 4× ускорение, потеря точности
    INT4 = 'int4'   # 4-битное квантование, экспериментально


class ModelFormat(Enum):
    PYTORCH = 'pytorch'
    ONNX = 'onnx'
    TENSORRT = 'tensorrt'
    OPENVINO = 'openvino'
    RKNN = 'rknn'
    COREML = 'coreml'  # для Apple Silicon (будущее)


_ULTRALYTICS_EXPORT_FORMAT: dict[str, str | None] = {
    ModelFormat.PYTORCH.value: None,
    ModelFormat.ONNX.value: 'onnx',
    ModelFormat.TENSORRT.value: 'engine',
    ModelFormat.OPENVINO.value: 'openvino',
    ModelFormat.RKNN.value: 'rknn',
    ModelFormat.COREML.value: 'coreml',
}

_EXPORT_EXTENSION: dict[str, str] = {
    ModelFormat.ONNX.value: '.onnx',
    ModelFormat.TENSORRT.value: '.engine',
    ModelFormat.OPENVINO.value: '_openvino_model',  # экспорт создаёт директорию
    ModelFormat.RKNN.value: '.rknn',
    ModelFormat.COREML.value: '.mlpackage',
}


def ultralytics_export_format(fmt: str) -> str | None:
    """Возвращает аргумент format для YOLO.export() по строке формата.
    """
    return _ULTRALYTICS_EXPORT_FORMAT.get(fmt)


def export_extension(fmt: str) -> str | None:
    """Вернуть расширение файла (или директории) артефакта экспорта."""
    return _EXPORT_EXTENSION.get(fmt)


class ModelSize(Enum):
    NANO = 'n'      # ~3M params, fastest
    SMALL = 's'     # ~11M params, balanced
    MEDIUM = 'm'    # ~26M params, accurate
    LARGE = 'l'     # ~44M params, high-accuracy
    XLARGE = 'x'    # ~68M params, max-accuracy


class ModelFamily(Enum):
    YOLOV5 = 'yolov5'
    YOLOV8 = 'yolov8'
    YOLOV10 = 'yolov10'
    YOLOV11 = 'yolov11'
    YOLOV12 = 'yolov12'  # placeholder для будущих версий
    YOLO26 = 'yolo26'
    PRISM = 'prism'      # Acmenra custom architecture
    RTDETR = 'rtdetr'    # Real-time DETR
    EFFICIENTDET = 'efficientdet'



class MetricType(Enum):
    FPS = 'fps'

    # Ресурсы
    GPU_UTIL = 'gpu_utilization'
    CPU_UTIL = 'cpu_utilization'
    VRAM_USAGE = 'vram_usage_mb'
    RAM_USAGE = 'ram_usage_mb'

    # Энергия и термо
    POWER_WATT = 'power_watt'
    TEMP_GPU_C = 'temp_gpu_c'
    TEMP_CPU_C = 'temp_cpu_c'

    # Точность (если есть ground truth)
    MAP_50 = 'map_50'
    MAP_50_95 = 'map_50_95'


class BaseMetric:
    """Базовая заглушка для будущих enum/entity метрик."""


class Metric(BaseMetric):
    def __init__(self, metric_uuid: UUID, counter: int, metric_type: MetricType):
        self.uuid = metric_uuid # Общий, полностью уникальный id
        self.counter = counter # номер "прогона"
        self.value = 0 # значение
        self._metric_type = metric_type # тип значения


class Coco(Enum):
    person = 0
    bicycle = 1
    car = 2
    motorcycle = 3
    airplane = 4
    bus = 5
    train = 6
    truck = 7
    boat = 8
    traffic_light = 9
    fire_hydrant = 10
    stop_sign = 11
    parking_meter = 12
    bench = 13
    bird = 14
    cat = 15
    dog = 16
    horse = 17
    sheep = 18
    cow = 19
    elephant = 20
    bear = 21
    zebra = 22
    giraffe = 23
    backpack = 24
    umbrella = 25
    handbag = 26
    tie = 27
    suitcase = 28
    frisbee = 29
    skis = 30
    snowboard = 31
    sports_ball = 32
    kite = 33
    baseball_bat = 34
    baseball_glove = 35
    skateboard = 36
    surfboard = 37
    tennis_racket = 38
    bottle = 39
    wine_glass = 40
    cup = 41
    fork = 42
    knife = 43
    spoon = 44
    bowl = 45
    banana = 46
    apple = 47
    sandwich = 48
    orange = 49
    broccoli = 50
    carrot = 51
    hot_dog = 52
    pizza = 53
    donut = 54
    cake = 55
    chair = 56
    couch = 57
    potted_plant = 58
    bed = 59
    dining_table = 60
    toilet = 61
    tv = 62
    laptop = 63
    mouse = 64
    remote = 65
    keyboard = 66
    cell_phone = 67
    microwave = 68
    oven = 69
    toaster = 70
    sink = 71
    refrigerator = 72
    book = 73
    clock = 74
    vase = 75
    scissors = 76
    teddy_bear = 77
    hair_drier = 78
    toothbrush = 79

    @classmethod
    def has_value(cls, value: int) -> bool:
        """Check if a given integer is a valid class ID."""
        return value in cls._value2member_map_

    @classmethod
    def name_of(cls, value: int) -> str:
        """Get class name by integer value."""
        if not cls.has_value(value):
            raise ValueError(f"Class ID {value} is not in COCO 2017 dataset.")
        return cls(value).name.replace('_', ' ').title()

    @classmethod
    def to_dict(cls) -> dict:
        """Convert enum to dictionary {id: 'name'}."""
        return {member.value: member.name.replace('_', ' ').title() for member in cls}
