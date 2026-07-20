# infrastructure/metrics/quality.py

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from core.entities.metrics import QualityMetrics

logger = logging.getLogger(__name__)


class QualityMetricsCollector(ABC):
    """Базовый класс для сборщиков метрик качества моделей."""

    @abstractmethod
    def collect(self) -> QualityMetrics:
        """Собирает метрики качества.
        
        Returns:
            QualityMetrics с заполненными полями quality metrics
            или с None в полях, если метрики не удалось рассчитать.
        """
        ...


class YOLOQualityMetricsCollector(QualityMetricsCollector):
    """Сборщик метрик качества для моделей.
    
    Использует встроенную функцию валидации для расчёта:
        - Recall, Precision, F1-Score
        - mAP50, mAP50-95
    """

    def __init__(
        self,
        yolo_backend: Any,
        dataset_path: Path | str,
        imgsz: int = 640,
        conf_threshold: float = 0.25,
    ) -> None:
        
        self.yolo_backend = yolo_backend
        self.yolo_model = yolo_backend.model if hasattr(yolo_backend, "model") else yolo_backend
        self.dataset_path = self._resolve_dataset_config(Path(dataset_path))
        self.imgsz = imgsz
        self.conf_threshold = conf_threshold
        self._cached_metrics: QualityMetrics | None = None

    def collect(self) -> QualityMetrics:
        """Собирает метрики качества модели.
        
        Запускает валидацию модели на датасете и извлекает метрики.
        
        Returns:
            QualityMetrics с заполненными recall, precision, f1-score, mAP50, mAP50-95.
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
        """Запускает валидацию и извлекает метрики из результатов.
        
        Returns:
            QualityMetrics с заполненными полями.
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
                task="detect",
                verbose=False,
            )

            # Извлекаем метрики из результатов
            recall = self._safe_float(results.box.mr, "mean recall")
            precision = self._safe_float(results.box.mp, "mean precision")
            
            # Вычисляем F1-score из precision и recall
            if recall is not None and precision is not None:
                if recall + precision > 0:
                    f1_score = 2 * (precision * recall) / (precision + recall)
                else:
                    f1_score = None
            else:
                f1_score = None
            
            map50 = self._safe_float(results.box.map50, "map50")
            map50_95 = self._safe_float(results.box.map, "map50-95")

            logger.info(
                "Метрики качества: recall=%.4f, precision=%.4f, "
                "f1=%.4f, map50=%.4f, map50_95=%.4f",
                recall or 0.0,
                precision or 0.0,
                f1_score or 0.0,
                map50 or 0.0,
                map50_95 or 0.0,
            )

            return QualityMetrics(
                recall=recall,
                precision=precision,
                f1_score=f1_score,
                map50=map50,
                map50_95=map50_95,
            )

        except Exception as e:
            logger.error("Ошибка при валидации модели: %s", e)
            raise

    @staticmethod
    def _resolve_dataset_config(dataset_path: Path) -> Path:
        """Вернуть YAML-конфиг датасета, если вместо него передали папку."""
        if dataset_path.is_dir():
            dataset_config = dataset_path / "data.yaml"
            if dataset_config.is_file():
                return dataset_config

        return dataset_path

    @staticmethod
    def _safe_float(value: Any, field_name: str) -> float | None:
        """Преобразует значение в float.
        """
        if value is None:
            return None

        try:
            result = float(value)
            # Нормализуем значение в диапазон [0, 1] если необходимо
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
