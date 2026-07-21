"""Постобработка сырых выходов модели (NMS, боксы, маски).

Нужна для ONNX/OpenVINO/TensorRT: их `predict()` в остальном отдаёт только
сырой тензор с выхода сети. В реальном сценарии (камера на устройстве) без
этого шага результат бесполезен — нельзя ни нарисовать рамку, ни принять
решение по детекции, пока не сделан NMS. Поэтому это часть измеряемого
`predict()`, а не отдельный необязательный шаг — так же, как для PyTorch эту
работу уже делает сама ultralytics внутри своего `predict()`. Используем
NMS/decode из ultralytics (`utils.nms`, `utils.ops`), не реализуем свои.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from ultralytics.engine.results import Results
from ultralytics.utils.nms import non_max_suppression
from ultralytics.utils.ops import process_mask, scale_boxes, scale_masks

_MASK_COEFFS = 32  # число mask-коэффициентов в выходе ultralytics segment-моделей


@dataclass
class Detections:
    """Финальные детекции в координатах исходного (не letterboxed) изображения."""

    boxes: np.ndarray
    """(N, 4) xyxy, пиксели исходного изображения."""
    scores: np.ndarray
    """(N,) confidence."""
    classes: np.ndarray
    """(N,) индекс класса."""
    masks: np.ndarray | None = None
    """(N, H, W) бинарные маски в разрешении исходного изображения — только
    для `task == "segment"`, иначе `None`."""


def postprocess_raw_output(
    raw_outputs: list[np.ndarray],
    letterboxed_shape: tuple[int, int],
    orig_shape: tuple[int, int],
    task: str,
    confidence_threshold: float = 0.25,
) -> Detections:
    """NMS + рескейл боксов/масок из letterboxed в исходное разрешение.

    Args:
        raw_outputs: Все выходные тензоры модели как есть (порядок не важен —
            детекционный тензор ищется по числу измерений: `ndim == 3`;
            proto-маски сегментации, если есть — `ndim == 4`).
        letterboxed_shape: `(height, width)` входа модели (см. `to_model_input`).
        orig_shape: `(height, width)` исходного изображения.
        task: ``"detect"`` или ``"segment"``.
        confidence_threshold: Порог confidence для NMS.

    Returns:
        `Detections` в координатах исходного изображения.
    """
    detect_raw = next(r for r in raw_outputs if r.ndim == 3)
    proto_raw = next((r for r in raw_outputs if r.ndim == 4), None)

    detect_tensor = torch.from_numpy(detect_raw).float()
    nm = _MASK_COEFFS if task == "segment" and proto_raw is not None else 0
    nc = detect_tensor.shape[1] - 4 - nm

    preds = non_max_suppression(
        detect_tensor, conf_thres=confidence_threshold, iou_thres=0.7, nc=nc
    )[0]

    if preds.shape[0] == 0:
        empty_masks = np.zeros((0, *orig_shape), dtype=np.uint8) if nm else None
        return Detections(
            boxes=np.zeros((0, 4)), scores=np.zeros(0), classes=np.zeros(0), masks=empty_masks
        )

    boxes = preds[:, :4]
    masks = None
    if nm:
        protos = torch.from_numpy(proto_raw[0]).float()
        letterboxed_masks = process_mask(
            protos, preds[:, 6:], boxes, letterboxed_shape, upsample=True
        )
        masks = (
            scale_masks(letterboxed_masks[:, None].float(), orig_shape)[:, 0]
            .gt_(0.5)
            .byte()
            .numpy()
        )

    boxes_orig = scale_boxes(letterboxed_shape, boxes.clone(), orig_shape)
    return Detections(
        boxes=boxes_orig.numpy(),
        scores=preds[:, 4].numpy(),
        classes=preds[:, 5].numpy().astype(int),
        masks=masks,
    )


def render_detections(
    image: np.ndarray, detections: Detections, names: dict[int, str]
) -> np.ndarray:
    """Отрисовать `detections` (см. `postprocess_raw_output`) поверх `image`.

    Переиспользует `ultralytics.engine.results.Results.plot()` — тот же
    визуальный стиль (цвета по классам, подписи, полупрозрачные маски), что
    и у PyTorch-бэкенда, вместо своей реализации рисования.
    """
    boxes_tensor = None
    masks_tensor = None
    if detections.boxes.shape[0]:
        boxes_tensor = torch.from_numpy(
            np.concatenate(
                [detections.boxes, detections.scores[:, None], detections.classes[:, None]],
                axis=1,
            ).astype(np.float32)
        )
        if detections.masks is not None:
            masks_tensor = torch.from_numpy(detections.masks).float()

    result = Results(orig_img=image, path="", names=names, boxes=boxes_tensor, masks=masks_tensor)
    return result.plot()
