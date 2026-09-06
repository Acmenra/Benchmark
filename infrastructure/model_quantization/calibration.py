import cv2
import yaml
import glob
import logging
import numpy as np
from typing import Any
from pathlib import Path

from infrastructure.exceptions import CalibrationDataError


logger = logging.getLogger(__name__)


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")


def collect_calibration_images(dataset_config_path: Path,
                               max_samples: int = 32) -> list[Path]:
    """
    Finds images for INT8 calibration based on an Ultralytics data.yaml file.

    Args:
        dataset_config_path: Path to the dataset configuration YAML file.
        max_samples: Maximum number of images to return for calibration.

    Returns:
        list[Path]: A list of resolved image paths, truncated to `max_samples`.

    Raises:
        CalibrationDataError: If the YAML is missing, lacks image sources,
                              or no valid images are found.
    """
    dataset_config_path = Path(dataset_config_path)
    if not dataset_config_path.is_file():
        raise CalibrationDataError(f"data.yaml не найден: {dataset_config_path}")

    with dataset_config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    dataset_root = _resolve_dataset_root(dataset_config_path, data.get("path"))
    image_source = data.get("val") or data.get("test") or data.get("train")
    if image_source is None:
        raise CalibrationDataError("В data.yaml нет train/val/test для калибровки")

    image_paths = _resolve_image_paths(dataset_root, dataset_config_path, image_source)
    if not image_paths:
        raise CalibrationDataError(f"Изображения для калибровки не найдены: {image_source}")

    return image_paths[:max_samples]


def preprocess_yolo_image(image_path: Path,
                          input_size: int) -> np.ndarray:
    """
    Prepares an image for YOLO model inference in NCHW float32 format.

    Args:
        image_path: Path to the input image.
        input_size: Target spatial resolution (e.g., 640).

    Returns:
        np.ndarray: A preprocessed image tensor of shape (1, 3, input_size, input_size).

    Raises:
        CalibrationDataError: If the image cannot be read by OpenCV.
    """
    image = cv2.imread(str(image_path))
    if image is None:
        raise CalibrationDataError(f"Не удалось прочитать изображение: {image_path}")

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (input_size, input_size), interpolation=cv2.INTER_LINEAR)
    image = image.astype(np.float32) / 255.0
    image = np.transpose(image, (2, 0, 1))
    return np.expand_dims(image, axis=0)


def _resolve_dataset_root(dataset_config_path: Path,
                          raw_root: Any) -> Path:
    """
    Determines the dataset root directory, handling various data.yaml configurations.

    Args:
        dataset_config_path: Path to the data.yaml file.
        raw_root: The 'path' value from the YAML (can be None, relative, or absolute).

    Returns:
        Path: The resolved absolute path to the dataset root.
    """
    if raw_root is None:
        return dataset_config_path.parent

    root = Path(str(raw_root)).expanduser()
    if root.is_absolute():
        return root

    parent_candidate = dataset_config_path.parent / root
    if parent_candidate.exists():
        return parent_candidate

    cwd_candidate = Path.cwd() / root
    if cwd_candidate.exists():
        return cwd_candidate

    return parent_candidate


def _resolve_image_paths(dataset_root: Path,
                         dataset_config_path: Path,
                         image_source: Any) -> list[Path]:
    """
    Expands a path or list of paths from data.yaml into a list of image files.

    Supports "lazy" paths with `../`, which are common in Ultralytics datasets,
    even when data.yaml is located in the root directory. If a `../` path fails,
    it automatically attempts to interpret it relative to the dataset root.

    Args:
        dataset_root: The resolved root directory of the dataset.
        dataset_config_path: Path to the data.yaml file.
        image_source: A string, Path, or list of strings/Paths from the YAML.

    Returns:
        list[Path]: A sorted, unique list of resolved image file paths.
    """
    if isinstance(image_source, (list, tuple)):
        paths: list[Path] = []
        for item in image_source:
            paths.extend(_resolve_image_paths(dataset_root, dataset_config_path, item))
        return sorted(set(paths))

    source = Path(str(image_source)).expanduser()
    candidates = []

    if source.is_absolute():
        candidates.append(source)
    else:
        candidates.extend([
            dataset_root / source,
            dataset_config_path.parent / source,
            Path.cwd() / source,
        ])

        source_str = str(source)
        if source_str.startswith("../"):
            cleaned_source = source_str
            while cleaned_source.startswith("../"):
                cleaned_source = cleaned_source[3:]

            cleaned_path = Path(cleaned_source)
            candidates.extend([
                dataset_root / cleaned_path,
                dataset_config_path.parent / cleaned_path,
                Path.cwd() / cleaned_path,
            ])

    for candidate in candidates:
        if candidate.is_dir():
            return _collect_images_from_directory(candidate)
        if candidate.is_file():
            return _collect_images_from_file(candidate)

    return []


def _collect_images_from_directory(directory: Path) -> list[Path]:
    """Recursively or flatly collects images from a directory."""
    image_paths: list[Path] = []
    for extension in IMAGE_EXTENSIONS:
        image_paths.extend(
            Path(path)
            for path in glob.glob(str(directory / f"*{extension}"))
        )
        image_paths.extend(
            Path(path)
            for path in glob.glob(str(directory / f"*{extension.upper()}"))
        )
    return sorted(image_paths)


def _collect_images_from_file(file_path: Path) -> list[Path]:
    """Reads a text file containing a list of image paths."""
    image_paths: list[Path] = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw_path = line.strip()
            if not raw_path:
                continue

            image_path = Path(raw_path).expanduser()
            if not image_path.is_absolute():
                image_path = file_path.parent / image_path
            if image_path.is_file():
                image_paths.append(image_path)

    return sorted(image_paths)