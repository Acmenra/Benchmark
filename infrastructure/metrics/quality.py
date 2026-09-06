# infrastructure/metrics/quality.py

import logging
from typing import Any
from pathlib import Path
from abc import ABC, abstractmethod
from core.enums.model import TaskType
from core.domain.metrics import QualityMetrics


logger = logging.getLogger(__name__)


class QualityMetricsCollector(ABC):
    """
    Abstract base class defining the contract for quality metric collection.

    Subclasses must implement the `collect` method to execute model validation
    and return aggregated accuracy metrics.
    """

    @abstractmethod
    def collect(self) -> QualityMetrics:
        """
        Executes the quality metric collection process.

        Returns:
            QualityMetrics: An immutable domain object with populated quality
                            fields, or an empty object if calculation fails.
        """
        ...


class YOLOQualityMetricsCollector(QualityMetricsCollector):
    """
    Concrete implementation of quality metrics collection for Ultralytics YOLO models.

    This collector leverages the built-in YOLO validation routine (`model.val()`)
    to compute standard COCO evaluation metrics. It includes intelligent fallback
    logic to handle different task types (detect, segment, pose, obb) and caches
    the results to avoid redundant, time-consuming validation runs.

    Key design decisions:
    - Caching: The first successful `collect()` call caches the result.
    - Task-aware parsing: Dynamically selects the correct metric namespace
      (e.g., `results.seg` for segmentation, `results.box` for detection).
    - Safe type conversion: Validates and bounds-checks all extracted floats.
    """

    def __init__(self,
                 yolo_backend: Any,
                 dataset_path: Path | str,
                 task_type: TaskType | str = TaskType.DETECT,
                 imgsz: int = 640,
                 conf_threshold: float = 0.25) -> None:
        """
        Initializes the YOLO quality metrics collector.

        Args:
            yolo_backend: The inference backend containing the YOLO model.
            dataset_path: Path to the validation dataset or its `data.yaml` config.
            task_type: The computer vision task (e.g., DETECT, SEGMENT).
            imgsz: The inference image resolution.
            conf_threshold: The confidence threshold for detection filtering.
        """
        self.yolo_backend = yolo_backend
        self.yolo_model = yolo_backend.model if hasattr(yolo_backend, "model") else yolo_backend
        self.dataset_path = self._resolve_dataset_config(Path(dataset_path))
        self.task_type = self._normalize_task_type(task_type)
        self.imgsz = imgsz
        self.conf_threshold = conf_threshold
        self._cached_metrics: QualityMetrics | None = None

    def collect(self) -> QualityMetrics:
        """
        Collects and returns the model's quality metrics.

        If metrics have already been collected, returns the cached result to
        save computation time. Otherwise, triggers `_run_validation()`.

        Returns:
            QualityMetrics: Populated with recall, precision, f1-score, mAP50, mAP50-95.
        """
        if self._cached_metrics is not None:
            logger.debug("Возвращаю закэшированные метрики качества")
            return self._cached_metrics

        try:
            metrics = self._run_validation()
            self._cached_metrics = metrics
            return metrics
        except Exception as e:
            logger.exception("Ошибка при сборе метрик качества: %s", e)
            return QualityMetrics()

    def _run_validation(self) -> QualityMetrics:
        """
        Executes the YOLO validation routine and extracts the metrics.

        Returns:
            QualityMetrics: A fully populated domain object with accuracy metrics.
        """
        try:
            logger.info(
                "Запуск валидации YOLO на датасете: %s",
                self.dataset_path,
            )

            results = self.yolo_model.val(
                data=str(self.dataset_path),
                imgsz=self.imgsz,
                conf=self.conf_threshold,
                task=self.task_type.value,
                verbose=False,
            )

            metrics_source = self._select_metrics_source(results)

            recall = self._safe_float(
                getattr(metrics_source, "mr", None),
                "mean recall",
            )
            precision = self._safe_float(
                getattr(metrics_source, "mp", None),
                "mean precision",
            )
            
            if recall is not None and precision is not None:
                if recall + precision > 0:
                    f1_score = 2 * (precision * recall) / (precision + recall)
                else:
                    f1_score = None
            else:
                f1_score = None
            
            map50 = self._safe_float(getattr(metrics_source, "map50", None), "map50")
            map50_95 = self._safe_float(getattr(metrics_source, "map", None), "map50-95")

            logger.info(
                "Метрики качества: recall=%.4f, precision=%.4f, "
                "f1=%.4f, map50=%.4f, map50_95=%.4f",
                recall or 0.0,
                precision or 0.0,
                f1_score or 0.0,
                map50 or 0.0,
                map50_95 or 0.0,
            )

            return QualityMetrics(recall=recall,
                                  precision=precision,
                                  f1_score=f1_score,
                                  map50=map50,
                                  map50_95=map50_95)

        except Exception as e:
            logger.error("Ошибка при валидации модели: %s", e)
            raise

    @staticmethod
    def _resolve_dataset_config(dataset_path: Path) -> Path:
        """
        Resolves the dataset configuration path.

        If a directory is provided, it automatically appends `data.yaml`
        if the file exists, ensuring compatibility with Ultralytics expectations.

        Args:
            dataset_path: The input path (directory or file).

        Returns:
            Path: The resolved path to the `data.yaml` configuration file.
        """
        if dataset_path.is_dir():
            dataset_config = dataset_path / "data.yaml"
            if dataset_config.is_file():
                return dataset_config

        return dataset_path

    @staticmethod
    def _normalize_task_type(task_type: TaskType | str) -> TaskType:
        """
        Normalizes the task type input to a standard `TaskType` enum.

        Args:
            task_type: The task type as a string or enum.

        Returns:
            TaskType: The normalized enum value.
        """
        if isinstance(task_type, TaskType):
            return task_type
        return TaskType(str(task_type).strip().lower())

    def _select_metrics_source(self,
                               results: Any) -> Any:
        """
        Selects the correct metrics namespace based on the current task type.

        Args:
            results: The raw results object returned by `yolo_model.val()`.

        Returns:
            Any: The specific metrics object (e.g., `results.seg`), or the
                 root `results` object as a fallback.
        """
        candidates_by_task = {
            TaskType.SEGMENT.value: "seg",
            TaskType.POSE.value: "pose",
            TaskType.OBB.value: "obb",
        }
        candidate_name = candidates_by_task.get(self.task_type.value, "box")
        metrics_source = getattr(results, candidate_name, None)
        if metrics_source is not None:
            return metrics_source

        logger.warning(
            "В результатах validation нет секции %s для task_type=%s",
            candidate_name,
            self.task_type.value,
        )
        return getattr(results, "box", results)

    @staticmethod
    def _safe_float(value: Any,
                    field_name: str) -> float | None:
        """
        Safely converts a value to a float with bounds checking.

        Args:
            value: The value to convert.
            field_name: The name of the field (for logging purposes).

        Returns:
            float | None: The converted float, or `None` if conversion fails
                          or the value is out of the expected [0, 100] range.
        """
        if value is None:
            return None

        try:
            result = float(value)
            if not (0 <= result <= 100):
                logger.warning(
                    "Значение %s=%.4f выходит за пределы [0, 100]",
                    field_name,
                    result,
                )
            return result
        except (TypeError, ValueError) as e:
            logger.warning(
                "Не удалось преобразовать %s в float: %s", field_name, e
            )
            return None
