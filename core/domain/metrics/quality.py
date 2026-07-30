# core/domain/metrics/quality.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class QualityMetrics:
    """
    Aggregated model validation quality metrics.

    Captures the accuracy and reliability of the model's predictions against
    a ground-truth dataset, typically computed using standard object detection
    or segmentation evaluation protocols (e.g., COCO metrics).

    Attributes:
        recall (float | None): Ratio of true positive detections to all actual positives.
        precision (float | None): Ratio of true positive detections to all predicted positives.
        f1_score (float | None): Harmonic mean of precision and recall.
        map50 (float | None): Mean Average Precision at IoU threshold of 0.50.
        map50_95 (float | None): Mean Average Precision averaged over IoU thresholds from 0.50 to 0.95.

    Note:
        - Values are `None` if validation was skipped or failed.
        - `map50_95` is the primary metric for comparing overall model detection quality.
    """
    recall: float | None = None
    precision: float | None = None
    f1_score: float | None = None
    map50: float | None = None
    map50_95: float | None = None