"""Разрешение датасета для тестовых изображений и оценки точности.

FPS/latency и accuracy считаются на одной и той же директории с
изображениями — никакого отдельного "скачиваемого на лету" датасета для
accuracy. Разметка ищется по стандартной конвенции ultralytics
(`img2label_paths`): рядом с директорией `images/` должна лежать
директория `labels/` с YOLO-txt файлами того же имени. Если её нет —
точность на этом источнике посчитать нельзя, и вызывающий код должен
явно это пропустить, а не подставлять посторонний датасет.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_ROOT = Path(__file__).resolve().parent.parent / "data" / "test_images"

COCO80_NAMES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    4: "airplane",
    5: "bus",
    6: "train",
    7: "truck",
    8: "boat",
    9: "traffic light",
    10: "fire hydrant",
    11: "stop sign",
    12: "parking meter",
    13: "bench",
    14: "bird",
    15: "cat",
    16: "dog",
    17: "horse",
    18: "sheep",
    19: "cow",
    20: "elephant",
    21: "bear",
    22: "zebra",
    23: "giraffe",
    24: "backpack",
    25: "umbrella",
    26: "handbag",
    27: "tie",
    28: "suitcase",
    29: "frisbee",
    30: "skis",
    31: "snowboard",
    32: "sports ball",
    33: "kite",
    34: "baseball bat",
    35: "baseball glove",
    36: "skateboard",
    37: "surfboard",
    38: "tennis racket",
    39: "bottle",
    40: "wine glass",
    41: "cup",
    42: "fork",
    43: "knife",
    44: "spoon",
    45: "bowl",
    46: "banana",
    47: "apple",
    48: "sandwich",
    49: "orange",
    50: "broccoli",
    51: "carrot",
    52: "hot dog",
    53: "pizza",
    54: "donut",
    55: "cake",
    56: "chair",
    57: "couch",
    58: "potted plant",
    59: "bed",
    60: "dining table",
    61: "toilet",
    62: "tv",
    63: "laptop",
    64: "mouse",
    65: "remote",
    66: "keyboard",
    67: "cell phone",
    68: "microwave",
    69: "oven",
    70: "toaster",
    71: "sink",
    72: "refrigerator",
    73: "book",
    74: "clock",
    75: "vase",
    76: "scissors",
    77: "teddy bear",
    78: "hair drier",
    79: "toothbrush",
}


def default_test_images_dir(task: str) -> Path:
    """Директория с завезёнными в репозиторий тестовыми изображениями для `task`.

    Используется, когда пользователь не задал `benchmark.test_images` —
    ``data/test_images/detect/images`` или ``data/test_images/segment/images``,
    у каждой рядом лежит `labels/` с реальной разметкой (32 изображения).
    """
    return _DATA_ROOT / ("segment" if task == "segment" else "detect") / "images"


def resolve_accuracy_dataset(images_dir: Path | str, task: str) -> str | None:
    """Собрать YAML-датасет ultralytics из `images_dir`, если рядом есть разметка.

    Ожидается конвенция ultralytics: `images_dir` — директория `images`, а
    разметка лежит в соседней директории `labels` (`images_dir.parent / "labels"`,
    см. `img2label_paths`). Если разметки нет — точность посчитать нельзя.

    Args:
        images_dir: Директория с изображениями (та же, что используется для FPS).
        task: ``"detect"`` или ``"segment"`` — только для имени кэш-файла.

    Returns:
        Путь к сгенерированному YAML датасета, либо `None`, если валидной
        разметки не найдено.
    """
    images_dir = Path(images_dir)
    labels_dir = images_dir.parent / "labels"
    if not images_dir.is_dir() or not labels_dir.is_dir():
        return None

    images = sorted(
        p for p in images_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")
    )
    if not images or not any((labels_dir / f"{p.stem}.txt").is_file() for p in images):
        return None

    import yaml as pyyaml

    cache_dir = Path("./.model_cache").resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = cache_dir / f"accuracy_{task}_{images_dir.resolve().parent.name}.yaml"
    yaml_path.write_text(
        pyyaml.safe_dump(
            {
                # "train" никогда не используется (мы только вызываем model.val()),
                # но ultralytics требует оба ключа в любом датасете — дублируем val.
                "train": str(images_dir.resolve()),
                "val": str(images_dir.resolve()),
                "names": COCO80_NAMES,
            }
        ),
        encoding="utf-8",
    )
    return str(yaml_path)
