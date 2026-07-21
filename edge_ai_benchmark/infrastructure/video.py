"""Разбиение видео на кадры для бенчмарка (стриминг-сценарий).

Источник видео — как и с фото — директория: в неё можно положить один или
несколько видеофайлов, все они будут декодированы и объединены в общий
список кадров (см. `find_video_paths`/`load_video_frames`).
"""

from __future__ import annotations

import glob
import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".webm")


def is_video_file(path: str | Path) -> bool:
    """Проверить, является ли `path` файлом с расширением видео.

    Args:
        path: Путь к файлу (существование не проверяется).

    Returns:
        `True`, если расширение файла — одно из `VIDEO_EXTENSIONS`.
    """
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def find_video_paths(directory: str | Path) -> list[str]:
    """Найти все видеофайлы в директории.

    Args:
        directory: Директория для поиска (нерекурсивно).

    Returns:
        Отсортированный список путей к найденным видеофайлам.
    """
    paths: list[str] = []
    for ext in VIDEO_EXTENSIONS:
        paths.extend(glob.glob(str(Path(directory) / f"*{ext}")))
    return sorted(paths)


def load_video_frames(path: str | Path, max_frames: int = 300) -> list[np.ndarray]:
    """Декодировать видео в список кадров BGR/HWC.

    Кадры читаются последовательно от начала файла. Для длинных видео
    декодируется не больше `max_frames` кадров, чтобы не раздувать память —
    остальные кадры при необходимости переиспользуются циклически на этапе
    прогона (см. `application.benchmark_runner.run_single_benchmark`).

    Args:
        path: Путь к видеофайлу.
        max_frames: Максимум декодируемых кадров.

    Returns:
        Список кадров BGR/HWC. Пустой список, если файл не открылся или в
        нём нет кадров.
    """
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        logger.warning("Не удалось открыть видео: %s", path)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    logger.info(
        "Декодирую видео %s: ~%d кадров @ %.1f FPS, беру до %d кадров",
        path,
        total,
        fps,
        max_frames,
    )

    frames: list[np.ndarray] = []
    try:
        while len(frames) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(frame)
    finally:
        cap.release()

    if not frames:
        logger.warning("В видео %s не найдено кадров", path)
    return frames


def load_video_frames_from_directory(
    directory: str | Path, max_frames: int = 300
) -> list[np.ndarray]:
    """Декодировать кадры из всех видеофайлов в директории (один или несколько).

    `max_frames` — общий бюджет кадров на всю директорию, распределяется по
    найденным видео последовательно (первое видео декодируется до тех пор,
    пока не отдаст все свои кадры или не будет достигнут остаток бюджета,
    затем второе и т.д.).

    Args:
        directory: Директория с видеофайлами.
        max_frames: Максимум суммарно декодируемых кадров.

    Returns:
        Список кадров BGR/HWC из всех найденных видео. Пустой список, если
        видео в директории не найдено.
    """
    video_paths = find_video_paths(directory)
    if not video_paths:
        return []

    frames: list[np.ndarray] = []
    for video_path in video_paths:
        remaining = max_frames - len(frames)
        if remaining <= 0:
            break
        frames.extend(load_video_frames(video_path, max_frames=remaining))
    return frames
