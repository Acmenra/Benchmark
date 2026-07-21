"""Интерфейсы (порты) предметной области.

Конкретные реализации живут в ``infrastructure`` и подставляются в
``application`` по месту использования (dependency inversion): core описывает
контракт, infrastructure — как это сделать руками, application — когда и
зачем это вызывать.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from edge_ai_benchmark.core.entities import AccuracyResult, BenchmarkResult, ModelSpec


class ModelLoader(ABC):
    """Единый интерфейс загрузчика модели для всех форматов (PyTorch/ONNX/TensorRT/OpenVINO)."""

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Проверить, установлен ли рантайм, необходимый для этого формата.

        Returns:
            `True`, если необходимая библиотека импортируется в этом окружении.
        """

    @abstractmethod
    def load(self, spec: ModelSpec) -> None:
        """Загрузить модель, описанную `spec`, в память/на устройство.

        Args:
            spec: Описание модели (семейство, размер, формат, источник весов).

        Raises:
            RuntimeError: Если необходимый рантайм недоступен в этом окружении.
        """

    @abstractmethod
    def warmup(self, input_size: int, iterations: int) -> None:
        """Прогреть модель фиктивными прогонами перед замером метрик.

        Args:
            input_size: Размер стороны квадратного входного изображения.
            iterations: Количество прогревочных итераций.
        """

    @abstractmethod
    def predict(self, image: np.ndarray) -> Any:
        """Выполнить один инференс с полной постобработкой (NMS, маски).

        Как в реальном сценарии (камера на устройстве): без NMS/декодирования
        масок результат бесполезен, поэтому постобработка — часть измеряемого
        вызова, а не отдельный шаг. Для PyTorch это делает сама ultralytics
        внутри своего `predict()`; для ONNX/OpenVINO/TensorRT — общий хелпер
        `infrastructure.postprocessing.postprocess_raw_output` (переиспользует
        NMS/decode из ultralytics, не свою реализацию).

        Args:
            image: Входное изображение в формате BGR/HWC (numpy array).

        Returns:
            Результат инференса, специфичный для бэкенда (сырые ultralytics
            `Results` для PyTorch, `infrastructure.postprocessing.Detections`
            для остальных) — в обоих случаях уже с финальными боксами/масками.
        """

    def last_compute_ms(self) -> float | None:
        """Задержка "чистого" forward pass последнего `predict()`, в мс.

        Не абстрактный — по умолчанию `None` (нет такой телеметрии).
        Загрузчики, которые не получают её бесплатно от фреймворка (как
        PyTorch от ultralytics `result.speed`), должны замерять время только
        вокруг вызова инференса (без препроцессинга и H2D/D2H-передачи) и
        переопределять этот метод.

        Returns:
            Миллисекунды, либо `None`, если такая телеметрия недоступна.
        """
        return None

    @abstractmethod
    def evaluate_accuracy(self, dataset: str, task: str, run_id: str) -> AccuracyResult:
        """Оценить точность модели на датасете.

        Args:
            dataset: Путь/имя YAML-датасета в формате ultralytics.
            task: ``"detect"`` или ``"segment"``.
            run_id: Идентификатор текущего прогона `run` (тот же, что в имени
                файла результатов) — используется как имя подпапки внутри
                ``runs/<task>/``, чтобы по `runs/` было видно, какому прогону
                результатов принадлежит каждый набор диагностических картинок.

        Returns:
            Метрики точности (`AccuracyResult`).
        """

    @abstractmethod
    def annotate(self, image: np.ndarray) -> np.ndarray:
        """Вернуть кадр с отрисовкой по результату последнего `predict()`.

        Не запускает повторный инференс — рисует поверх уже посчитанных в
        `predict()` детекций тем же изображением; переиспользует
        `ultralytics.engine.results.Results.plot()` (свою отрисовку не пишем).

        Args:
            image: То же изображение, что было передано в предшествующий `predict()`.

        Returns:
            Аннотированный кадр BGR/HWC (боксы+классы+confidence, маски для
            задачи segment).
        """

    @abstractmethod
    def unload(self) -> None:
        """Освободить ресурсы модели (память/устройство)."""


class Reporter(ABC):
    """Единый интерфейс экспортёра результатов бенчмарка (JSON/CSV/Markdown/HTML)."""

    @abstractmethod
    def write(
        self,
        results: list[BenchmarkResult],
        system_info: dict[str, Any],
        path: str,
    ) -> None:
        """Записать отчёт по результатам бенчмарка в файл.

        Args:
            results: Список результатов по всем прогнанным комбинациям.
            system_info: Собранные характеристики системы.
            path: Путь к выходному файлу.
        """
