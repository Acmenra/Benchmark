from pathlib import Path

import cv2
import numpy as np

from infrastructure.model_quantization.calibration import (
    collect_calibration_images,
    preprocess_yolo_image,
)
from infrastructure.model_quantization.yolo_export import ensure_yolo_pt_model


def test_collect_calibration_images_from_ultralytics_yaml(tmp_path: Path) -> None:
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    image_path = images_dir / "sample.jpg"
    cv2.imwrite(str(image_path), np.zeros((8, 8, 3), dtype=np.uint8))

    dataset_config = tmp_path / "data.yaml"
    dataset_config.write_text(
        """
path: .
val: images
nc: 1
names:
  0: person
""",
        encoding="utf-8",
    )

    assert collect_calibration_images(dataset_config) == [image_path]


def test_preprocess_yolo_image_returns_nchw_float32(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.jpg"
    cv2.imwrite(str(image_path), np.zeros((8, 8, 3), dtype=np.uint8))

    result = preprocess_yolo_image(image_path, input_size=32)

    assert result.shape == (1, 3, 32, 32)
    assert result.dtype == np.float32


def test_ensure_yolo_pt_model_returns_existing_file(tmp_path: Path) -> None:
    model_path = tmp_path / "custom.pt"
    model_path.write_bytes(b"stub")

    assert ensure_yolo_pt_model(model_path) == model_path
