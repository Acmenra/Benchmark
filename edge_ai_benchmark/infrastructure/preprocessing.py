"""Предобработка изображений для бэкендов, не имеющих встроенного пайплайна ultralytics."""

from __future__ import annotations

import cv2
import numpy as np


def letterbox_resize(
    image: np.ndarray, size: int, color: tuple[int, int, int] = (114, 114, 114)
) -> np.ndarray:
    """Привести изображение к квадрату `size`×`size` с сохранением пропорций (letterbox).

    Args:
        image: Входное изображение BGR/HWC.
        size: Сторона выходного квадратного изображения.
        color: Цвет паддинга.

    Returns:
        Изображение `size`×`size`×3, BGR, dtype совпадает с входным.
    """
    h, w = image.shape[:2]
    scale = min(size / h, size / w)
    new_h, new_w = int(round(h * scale)), int(round(w * scale))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    canvas = np.full((size, size, 3), color, dtype=image.dtype)
    top = (size - new_h) // 2
    left = (size - new_w) // 2
    canvas[top : top + new_h, left : left + new_w] = resized
    return canvas


def to_model_input(image: np.ndarray, size: int) -> np.ndarray:
    """Подготовить letterboxed изображение к формату входного тензора модели.

    Args:
        image: Входное изображение BGR/HWC.
        size: Сторона квадратного входного изображения модели.

    Returns:
        Тензор формы `(1, 3, size, size)`, dtype float32, значения в [0, 1], каналы RGB.
    """
    letterboxed = letterbox_resize(image, size)
    rgb = cv2.cvtColor(letterboxed, cv2.COLOR_BGR2RGB)
    chw = rgb.transpose(2, 0, 1).astype(np.float32) / 255.0
    return np.expand_dims(chw, axis=0)
