import gc
import os
import cv2
import glob
import torch
import logging
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from typing import Generator
from dataclasses import dataclass

from acmenra_cv import YOLOBackend, Backend
from core.enums.model import DeviceType

from core.domain.config import BenchmarkConfig, BenchmarkCase, SystemInfoConfig
from application.benchmark.metrics.collector import MetricsCollector
from core.domain.metrics import ModelBenchmarkResult, LatencyStats, CPUMetrics, GPUMetrics, QualityMetrics

from core.enums.model import (
    Coco,
    QuantizationLevel,
    TaskType,
    export_extension,
    ultralytics_export_format,
)
from infrastructure.exceptions import ONNXQuantizationError
from infrastructure.exceptions.quantization.errors import (
    NCNNQuantizationError, TensorRTQuantizationError,
    OpenVINOQuantizationError, PyTorchQuantizationError
)
from infrastructure.hardware.collectors.cpu import CPUCollector
from infrastructure.hardware.collectors.gpu import GPUCollector
from infrastructure.hardware.collectors.ram import RAMCollector
from infrastructure.metrics.cpu import CPUMetricsCollector
from infrastructure.metrics.gpu import GPUMetricsCollector
from infrastructure.metrics.quality import YOLOQualityMetricsCollector

from infrastructure.model_quantization.onnx import ONNXINT8Quantizer
from infrastructure.model_quantization.openvino import OpenVINOFP16Quantizer, OpenVINOINT8Quantizer
from infrastructure.model_quantization.pytorch import PyTorchINT8Quantizer
from infrastructure.model_quantization.tensorrt import TensorRTFP16Quantizer, TensorRTINT8Quantizer
from infrastructure.model_quantization.ncnn import NCNNFP32Exporter, NCNNINT8Quantizer
from infrastructure.model_quantization.yolo_export import ModelExportError, ensure_yolo_pt_model, export_yolo_model


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ResolvedModelArtifact:
    """Фактически выбранный артефакт модели."""
    path: Path
    quantization: str


class BenchmarkRunner:
    """Координирует загрузку модели, инференс и сбор метрик."""

    def __init__(self, benchmark_config: BenchmarkConfig, system_info_config: SystemInfoConfig | None = None) -> None:
        self.benchmark_config = benchmark_config

        self.models_dir = benchmark_config.models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)

        safe_config = system_info_config or SystemInfoConfig(collect_cpu=True, collect_gpu=True)
        self.cpu = CPUCollector(system_info_config=safe_config)
        self.gpu = GPUCollector(system_info_config=safe_config)
        self.ram = RAMCollector(system_info_config=safe_config)

    def run_suite(self) -> Generator[ModelBenchmarkResult, None, None]:
        """Запустить все benchmark-кейсы и возвращать результаты по мере готовности."""
        for case in self.benchmark_config.runs:
            yield from self._run_case(case)

    def _run_case(self, case: BenchmarkCase) -> Generator[ModelBenchmarkResult, None, None]:
        """Выполнить один benchmark-кейс и возвращать результаты моделей по мере готовности."""
        dataset_path = self._get_dataset_path()
        input_size = self.benchmark_config.input_size or 640
        main_iterations = self.benchmark_config.main_iterations or 100

        # 1. БЕЗОПАСНОЕ ОПРЕДЕЛЕНИЕ ИСТОЧНИКА ДАННЫХ
        if dataset_path is not None:
            logger.info(f"Использую реальный датасет: {dataset_path}")
            data_source = self._collect_image_paths(dataset_path)
            is_synthetic = False
        else:
            logger.info("Режим синтетических данных: генерирую кадры np.zeros для замера чистой производительности.")
            data_source = [np.zeros((input_size, input_size, 3), dtype=np.uint8) for _ in range(main_iterations)]
            is_synthetic = True

        # 2. ПОЛУЧЕНИЕ СПИСКА УСТРОЙСТВ
        devices_to_test = getattr(self.benchmark_config, 'devices', None)
        if not devices_to_test:
            fallback = self.benchmark_config.device_type or DeviceType.CPU
            devices_to_test = [fallback]

        for model_config in case.models:
            family = model_config.family
            size = model_config.size

            # 3. ЦИКЛ ПО УСТРОЙСТВАМ
            for device in devices_to_test:
                # Нормализуем устройство. Если оно недоступно, вернется None
                normalized_device = self._normalize_device(device)

                # Определяем имя устройства для записи в CSV (даже если оно недоступно)
                device_name_for_csv = str(device).lower() if isinstance(device, str) else getattr(device, 'value',
                                                                                                  str(device)).lower()

                if normalized_device is None:
                    logger.warning(
                        f"⚠️ Устройство '{device}' недоступно или не распознано. Все тесты для него будут помечены как skipped.")
                else:
                    logger.info(f"--- Запуск бенчмарка на устройстве: {device_name_for_csv.upper()} ---")

                for format_ in self._get_supported_formats():
                    for quantization in self._get_quantization_levels():

                        # ЕСЛИ УСТРОЙСТВО НЕДОСТУПНО, СРАЗУ ПИШЕМ SKIPPED В ОТЧЕТ И ИДЕМ ДАЛЬШЕ
                        if normalized_device is None:
                            yield self._build_status_result(
                                family=family, size=size, format_=format_,
                                actual_quantization=quantization, status="skipped",
                                error=f"Устройство '{device}' недоступно на этой системе",
                                device=device_name_for_csv
                            )
                            continue

                        # ДАЛЕЕ ИДЕТ ОБЫЧНАЯ ЛОГИКА ТОЛЬКО ДЛЯ ДОСТУПНЫХ УСТРОЙСТВ
                        artifact = self.resolve_model_artifact(family, size, format_, quantization)

                        if artifact is None:
                            yield self._build_status_result(
                                family=family, size=size, format_=format_,
                                actual_quantization=quantization, status="skipped",
                                error="Модель не подготовлена: формат или квантование не поддержаны текущим pipeline",
                                device=device_name_for_csv
                            )
                            continue

                        # 4. ЯВНОЕ СОЗДАНИЕ ЦЕПОЧКИ СБОРЩИКОВ
                        collector = MetricsCollector(
                            benchmark_case=case,
                            cpu_collector=CPUMetricsCollector(interval_seconds=0.1, cpu_collector=self.cpu),
                            gpu_collector=GPUMetricsCollector(interval_seconds=0.1, gpu_collector=self.gpu),
                        )

                        model: YOLOBackend | None = None
                        run_failed = False
                        try:
                            model = self._build_yolo_backend(artifact.path, artifact.quantization,
                                                             override_device=normalized_device)
                            self._warmup(model)
                            collector.start_run()
                            self._run_model_on_data(model, data_source, collector, is_synthetic)
                        except Exception as error:
                            logger.exception("Ошибка benchmark-прогона %s%s/%s/%s на %s", family, size, format_,
                                             quantization, device_name_for_csv)
                            run_failed = True
                            raw_result = self._safe_get_collector_result(collector)
                            yield self._build_status_result(
                                family=family, size=size, format_=format_,
                                actual_quantization=artifact.quantization, status="failed",
                                error=str(error), performance=raw_result.performance,
                                cpu=raw_result.cpu, gpu=raw_result.gpu,
                                device=device_name_for_csv
                            )
                            self._finalize_run(collector, model)
                            continue

                        raw_result = self._safe_get_collector_result(collector)

                        try:
                            quality_metrics = self._collect_quality_metrics(model, family, size)
                        except Exception as error:
                            logger.warning("Не удалось собрать метрики качества для %s%s/%s/%s: %s", family, size,
                                           format_, quantization, error)
                            quality_metrics = None
                        finally:
                            self._finalize_run(collector, model)

                        yield ModelBenchmarkResult(
                            model={
                                "family": family,
                                "size": size,
                                "device": device_name_for_csv,
                                "task_type": self._get_task_type().value,
                                "format": format_,
                                "quantization": artifact.quantization,
                            },
                            status="success",
                            performance=raw_result.performance,
                            cpu=raw_result.cpu,
                            gpu=raw_result.gpu,
                            quality=quality_metrics,
                        )

    def _build_status_result(self,
                             family: str,
                             size: str,
                             format_: str,
                             actual_quantization: str | None,
                             status: str,
                             error: str | None, performance: LatencyStats | None = None,
                             cpu: CPUMetrics | None = None,
                             gpu: GPUMetrics | None = None,
                             device: str = "unknown") -> ModelBenchmarkResult:
        return ModelBenchmarkResult(
            model={"family": family, "size": size, "device": device, "task_type": self._get_task_type().value,
                   "format": format_, "quantization": actual_quantization},
            status=status,
            error=error,
            performance=performance,
            cpu=cpu,
            gpu=gpu,
            quality=None,
        )

    def _safe_get_collector_result(self, collector: MetricsCollector) -> object:
        try:
            return collector.get()
        except Exception as error:
            logger.warning("Не удалось получить метрики benchmark-прогона: %s", error)
            return type("FallbackBenchmarkResult", (), {"performance": None, "cpu": None, "gpu": None})()

    def _finalize_run(self, collector: MetricsCollector, model: YOLOBackend | None) -> None:
        try:
            collector.stop_run()
        except Exception as error:
            logger.exception("Не удалось остановить collector benchmark-прогона: %s", error)
        if model is None:
            return
        try:
            self._cleanup_model_resources(model)
        except Exception as error:
            logger.exception("Не удалось освободить ресурсы модели: %s", error)

    def _get_dataset_path(self) -> Path | None:
        path_str = self.benchmark_config.test_images
        if not path_str or str(path_str).lower() == "synthetic":
            return None
        dataset_path = Path(path_str)
        if dataset_path.suffix.lower() in (".yaml", ".yml"):
            logger.warning(
                f"В test_images указан YAML-файл ({dataset_path.name}), а не папка с данными. Переключаюсь на синтетические данные.")
            return None
        if not dataset_path.is_dir():
            logger.warning(
                f"Путь '{dataset_path}' не найден или не является директорией. Переключаюсь на синтетические данные.")
            return None
        if (dataset_path / "images").is_dir():
            return dataset_path / "images"
        if (dataset_path / "val" / "images").is_dir():
            return dataset_path / "val" / "images"
        if (dataset_path / "train" / "images").is_dir():
            return dataset_path / "train" / "images"
        return dataset_path

    def _collect_image_paths(self, dataset_path: Path) -> list[Path]:
        extensions = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
        image_paths: list[Path] = []
        for ext in extensions:
            image_paths.extend(Path(path) for path in glob.glob(os.path.join(dataset_path, f"*{ext}")))
            image_paths.extend(Path(path) for path in glob.glob(os.path.join(dataset_path, f"*{ext.upper()}")))
        if not image_paths:
            raise ValueError(f"No images found in {dataset_path}")
        return sorted(image_paths)

    def _get_supported_formats(self) -> tuple[str, ...]:
        return self.benchmark_config.formats or ("pytorch",)

    def _get_quantization_levels(self) -> tuple[str, ...]:
        return self.benchmark_config.quantization or (QuantizationLevel.FP32.value,)

    def _get_task_type(self) -> TaskType:
        return self.benchmark_config.task_type or TaskType.DETECT

    def _run_model_on_data(self, model: Backend, data_source: list[Path] | list[np.ndarray],
                           collector: MetricsCollector, is_synthetic: bool) -> None:
        main_iterations = self.benchmark_config.main_iterations or len(data_source)
        for iteration in range(main_iterations):
            if is_synthetic:
                frame = data_source[iteration % len(data_source)]
            else:
                img_path = data_source[iteration % len(data_source)]
                frame = cv2.imread(str(img_path))
                if frame is None:
                    logger.warning("Could not read %s, skipping", img_path)
                    continue
            collector.mark_start()
            try:
                model.predict(frame)
            finally:
                collector.mark_stop()

    def resolve_model_artifact(self, family: str, size: str, format_: str,
                               quantization: str = QuantizationLevel.FP32.value) -> ResolvedModelArtifact | None:
        return self._try_resolve_model_artifact(family, size, format_, self._normalize_quantization(quantization))

    def resolve_model_path(self, family: str, size: str, format_: str,
                           quantization: str = QuantizationLevel.FP32.value) -> Path | None:
        artifact = self.resolve_model_artifact(family, size, format_, quantization)
        return artifact.path if artifact is not None else None

    def _try_resolve_model_artifact(self, family: str, size: str, format_: str,
                                    quantization: str) -> ResolvedModelArtifact | None:
        """Возвращает путь к модели нужного формата."""
        quantization = self._normalize_quantization(quantization)
        if not self._is_quantization_supported(format_, quantization):
            return None

        model_stem = self._build_model_stem(family, size)
        pt_path = self.models_dir / f"{model_stem}.pt"

        # 1. PyTorch
        if format_ == "pytorch":
            if quantization == QuantizationLevel.INT8.value:
                int8_artifact = self._prepare_pytorch_int8_artifact(pt_path=pt_path, family=family, size=size)
                if int8_artifact is None: return None
                return ResolvedModelArtifact(path=int8_artifact, quantization=quantization)
            try:
                pt_path = ensure_yolo_pt_model(pt_path)
            except ModelExportError as error:
                logger.warning("Не удалось подготовить исходную .pt модель: %s", error)
                return None
            return ResolvedModelArtifact(path=pt_path, quantization=quantization)

        # 2. Подготовка путей для остальных форматов
        export_format = ultralytics_export_format(format_)
        extension = export_extension(format_)
        if export_format is None or extension is None:
            logger.warning("Неизвестный формат модели: %s", format_)
            return None

        cached = self._find_cached_artifact(family, size, extension, quantization)
        if cached is not None:
            logger.info("Найден закэшированный артефакт %s/%s: %s", format_, quantization, cached)
            return ResolvedModelArtifact(path=cached, quantization=quantization)

        try:
            pt_path = ensure_yolo_pt_model(pt_path)
        except ModelExportError as error:
            logger.warning("Не удалось подготовить исходную .pt модель: %s", error)
            return None

        # 3. OpenVINO FP16
        if format_ == "openvino" and quantization == QuantizationLevel.FP16.value:
            fp16_artifact = self._prepare_openvino_fp16_artifact(pt_path=pt_path, family=family, size=size,
                                                                 extension=extension)
            if fp16_artifact is None: return None
            return ResolvedModelArtifact(path=fp16_artifact, quantization=quantization)

        # 4. TensorRT FP16
        if format_ == "tensorrt" and quantization == QuantizationLevel.FP16.value:
            fp16_artifact = self._prepare_tensorrt_fp16_artifact(pt_path=pt_path, family=family, size=size)
            if fp16_artifact is None: return None
            return ResolvedModelArtifact(path=fp16_artifact, quantization=quantization)

        # 5. TensorRT INT8
        if format_ == "tensorrt" and quantization == QuantizationLevel.INT8.value:
            int8_artifact = self._prepare_tensorrt_int8_artifact(pt_path=pt_path, family=family, size=size)
            if int8_artifact is None: return None
            return ResolvedModelArtifact(path=int8_artifact, quantization=quantization)

        # 6. NCNN FP32
        if format_ == "ncnn" and quantization == QuantizationLevel.FP32.value:
            param_path = self._build_cached_artifact_path(family, size, ".param", quantization)
            bin_path = self._build_cached_artifact_path(family, size, ".bin", quantization)
            try:
                NCNNFP32Exporter().export(pt_path, param_path, bin_path)
                return ResolvedModelArtifact(path=param_path, quantization=quantization)
            except NCNNQuantizationError as error:
                logger.warning("Не удалось подготовить NCNN FP32 для %s%s: %s", family, size, error)
                return None

        # 7. NCNN INT8
        if format_ == "ncnn" and quantization == QuantizationLevel.INT8.value:
            int8_param_path = self._build_cached_artifact_path(family, size, ".param", quantization)
            int8_bin_path = self._build_cached_artifact_path(family, size, ".bin", quantization)
            dataset_config_path = self._find_quality_dataset_config()
            if dataset_config_path is None:
                logger.warning("NCNN INT8 требует data.yaml для калибровки, датасет не найден")
                return None
            input_size = self.benchmark_config.input_size or 640
            try:
                NCNNINT8Quantizer().quantize(
                    pt_path=pt_path, ncnn_int8_param_path=int8_param_path, ncnn_int8_bin_path=int8_bin_path,
                    dataset_config_path=dataset_config_path, input_size=input_size,
                )
                return ResolvedModelArtifact(path=int8_param_path, quantization=quantization)
            except NCNNQuantizationError as error:
                logger.warning("Не удалось подготовить NCNN INT8 для %s%s: %s", family, size, error)
                return None

        # 8. ONNX и OpenVINO INT8
        if quantization == QuantizationLevel.INT8.value and format_ in ("onnx", "openvino"):
            int8_artifact = self._prepare_int8_artifact(pt_path=pt_path, family=family, size=size, format_=format_,
                                                        extension=extension)
            if int8_artifact is None: return None
            return ResolvedModelArtifact(path=int8_artifact, quantization=quantization)

        # 9. Стандартный экспорт
        export_kwargs = self._build_export_kwargs(export_format, quantization)
        if export_kwargs is None:
            return None

        logger.info("Экспорт %s -> %s/%s", model_stem, format_, quantization)
        try:
            exported_path = export_yolo_model(
                pt_path=pt_path, export_format=export_format,
                target_path=self._build_cached_artifact_path(family, size, extension, quantization),
                export_kwargs=export_kwargs,
            )
        except (ModelExportError, Exception):
            logger.exception("Не удалось экспортировать %s в формат %s/%s", pt_path, format_, quantization)
            return None

        logger.info("Экспорт завершён: %s", exported_path)
        return ResolvedModelArtifact(path=exported_path, quantization=quantization)

    # =========================================================================
    # МЕТОДЫ ПОДГОТОВКИ АРТЕФАКТОВ
    # =========================================================================
    def _prepare_pytorch_int8_artifact(self, pt_path: Path, family: str, size: str) -> Path | None:
        int8_path = self._build_cached_artifact_path(family, size, ".pt", QuantizationLevel.INT8.value)
        dataset_config_path = self._find_quality_dataset_config()
        if dataset_config_path is None:
            logger.warning("PyTorch INT8 требует data.yaml, датасет не найден")
            return None
        try:
            return PyTorchINT8Quantizer().quantize(pt_path=pt_path, int8_pt_path=int8_path,
                                                   dataset_config_path=dataset_config_path,
                                                   input_size=self.benchmark_config.input_size or 640)
        except (PyTorchQuantizationError, Exception) as error:
            logger.warning("Не удалось подготовить PyTorch INT8 артефакт для %s%s: %s", family, size, error)
            return None

    def _prepare_tensorrt_fp16_artifact(self, pt_path: Path, family: str, size: str) -> Path | None:
        fp16_path = self._build_cached_artifact_path(family, size, ".engine", QuantizationLevel.FP16.value)
        try:
            return TensorRTFP16Quantizer().quantize(pt_path=pt_path, fp16_engine_path=fp16_path)
        except (TensorRTQuantizationError, Exception) as error:
            logger.warning("Не удалось подготовить TensorRT FP16 артефакт для %s%s: %s", family, size, error)
            return None

    def _prepare_tensorrt_int8_artifact(self, pt_path: Path, family: str, size: str) -> Path | None:
        int8_path = self._build_cached_artifact_path(family, size, ".engine", QuantizationLevel.INT8.value)
        dataset_config_path = self._find_quality_dataset_config()
        if dataset_config_path is None:
            logger.warning("TensorRT INT8 требует data.yaml, датасет не найден")
            return None
        try:
            return TensorRTINT8Quantizer().quantize(pt_path=pt_path, int8_engine_path=int8_path,
                                                    dataset_config_path=dataset_config_path,
                                                    input_size=self.benchmark_config.input_size or 640)
        except (TensorRTQuantizationError, Exception) as error:
            logger.warning("Не удалось подготовить TensorRT INT8 артефакт для %s%s: %s", family, size, error)
            return None

    def _prepare_openvino_fp16_artifact(self, pt_path: Path, family: str, size: str, extension: str) -> Path | None:
        fp32_path = self._build_cached_artifact_path(family, size, extension, QuantizationLevel.FP32.value)
        fp16_path = self._build_cached_artifact_path(family, size, extension, QuantizationLevel.FP16.value)
        try:
            return OpenVINOFP16Quantizer().quantize(pt_path=pt_path, fp32_openvino_path=fp32_path,
                                                    fp16_openvino_path=fp16_path)
        except (OpenVINOQuantizationError, ModelExportError, Exception) as error:
            logger.warning("Не удалось подготовить FP16 OpenVINO артефакт для %s%s: %s", family, size, error)
            return None

    def _prepare_int8_artifact(self, pt_path: Path, family: str, size: str, format_: str,
                               extension: str) -> Path | None:
        dataset_config_path = self._find_quality_dataset_config()
        if dataset_config_path is None:
            logger.warning("INT8 требует data.yaml для калибровки, датасет не найден")
            return None
        input_size = self.benchmark_config.input_size or 640
        fp32_path = self._build_cached_artifact_path(family, size, extension, QuantizationLevel.FP32.value)
        int8_path = self._build_cached_artifact_path(family, size, extension, QuantizationLevel.INT8.value)
        try:
            if format_ == "onnx":
                return ONNXINT8Quantizer().quantize(pt_path=pt_path, fp32_onnx_path=fp32_path, int8_onnx_path=int8_path,
                                                    dataset_config_path=dataset_config_path, input_size=input_size)
            if format_ == "openvino":
                return OpenVINOINT8Quantizer().quantize(pt_path=pt_path, fp32_openvino_path=fp32_path,
                                                        int8_openvino_path=int8_path,
                                                        dataset_config_path=dataset_config_path, input_size=input_size)
        except (ONNXQuantizationError, OpenVINOQuantizationError, ModelExportError, Exception) as error:
            logger.warning("Не удалось подготовить INT8 артефакт для %s%s/%s: %s", family, size, format_, error)
            return None
        logger.warning("INT8 quantizer для формата %s не реализован", format_)
        return None

    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================
    def _is_quantization_supported(self, format_: str, quantization: str) -> bool:
        if quantization == QuantizationLevel.FP32.value:
            return True
        if quantization == QuantizationLevel.INT4.value:
            logger.warning("INT4 пока не поддержан через Ultralytics export")
            return False

        supported_formats_by_quantization = {
            QuantizationLevel.FP16.value: {"onnx", "openvino", "tensorrt"},
            QuantizationLevel.INT8.value: {"onnx", "openvino", "tensorrt", "pytorch", "ncnn"},
        }
        supported_formats = supported_formats_by_quantization.get(quantization, set())
        if format_ not in supported_formats:
            logger.warning("Квантование %s для формата %s сейчас не поддержано, кейс будет пропущен", quantization,
                           format_)
            return False
        return True

    def _find_cached_artifact(self, family: str, size: str, extension: str, quantization: str) -> Path | None:
        candidate = self._build_cached_artifact_path(family, size, extension, quantization)
        return candidate if candidate.exists() else None

    def _build_cached_artifact_path(self, family: str, size: str, extension: str, quantization: str) -> Path:
        model_stem = self._build_model_stem(family, size)
        if quantization == QuantizationLevel.FP32.value:
            return self.models_dir / f"{model_stem}{extension}"
        return self.models_dir / f"{model_stem}_{quantization}{extension}"

    def _build_model_stem(self, family: str, size: str) -> str:
        return f"{family}{size}{self._get_task_model_suffix()}"

    def _get_task_model_suffix(self) -> str:
        suffixes_by_task = {TaskType.SEGMENT.value: "-seg", TaskType.POSE.value: "-pose",
                            TaskType.CLASSIFY.value: "-cls", TaskType.OBB.value: "-obb"}
        return suffixes_by_task.get(self._get_task_type().value, "")

    def _build_export_kwargs(self, export_format: str, quantization: str) -> dict[str, object] | None:
        export_kwargs: dict[str, object] = {"format": export_format}
        if quantization == QuantizationLevel.FP32.value:
            return export_kwargs
        if quantization == QuantizationLevel.FP16.value:
            export_kwargs["quantize"] = "fp16"
            return export_kwargs
        if quantization == QuantizationLevel.INT8.value:
            dataset_config_path = self._find_quality_dataset_config()
            if dataset_config_path is None:
                logger.warning("INT8 export требует data.yaml для калибровки, датасет не найден")
                return None
            export_kwargs["int8"] = True
            export_kwargs["data"] = str(dataset_config_path)
            return export_kwargs
        return None

    def _normalize_quantization(self, quantization: str) -> str:
        try:
            return QuantizationLevel(quantization).value
        except ValueError:
            logger.warning("Неизвестный уровень квантования %s, используется fp32", quantization)
            return QuantizationLevel.FP32.value

    def _build_yolo_backend(self, model_path: Path, quantization: str = QuantizationLevel.FP32.value,
                            override_device: DeviceType | None = None) -> YOLOBackend:
        # Двойная нормализация гарантирует, что в YOLOBackend попадет ТОЛЬКО Enum DeviceType
        target_device = override_device or self.benchmark_config.device_type
        device = self._normalize_device(target_device)

        # Если по какой-то причине device стал None, форсируем CPU, чтобы не упасть
        if device is None:
            device = DeviceType.CPU

        task_type = self._get_task_type()
        return YOLOBackend(
            model=YOLO(str(model_path), task=task_type.value),
            device=device,  # acmenra_cv строго требует DeviceType Enum
            category=Coco,
            task_type=task_type,
            threshold=self.benchmark_config.confidence_threshold or 0.25,
            iou=0.7,
            imgsz=self.benchmark_config.input_size or 640,
            half=quantization == QuantizationLevel.FP16.value,
        )

    def _normalize_device(self, device_type: DeviceType | str | None) -> DeviceType | None:
        """
        Пуленепробиваемая нормализация устройства.
        Возвращает DeviceType Enum, если устройство доступно.
        Возвращает None, если запрошенное устройство физически отсутствует.
        """
        if device_type is None:
            return DeviceType.CPU

        # Если пришел сам Enum, берем его строковое значение
        if isinstance(device_type, DeviceType):
            device_str = device_type.value.lower()
        else:
            device_str = str(device_type).strip().lower()

        if device_str == 'auto':
            if torch.cuda.is_available():
                return DeviceType.CUDA
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return DeviceType.MPS
            return DeviceType.CPU

        if device_str == 'cuda':
            if torch.cuda.is_available():
                return DeviceType.CUDA
            logger.warning("⚠️ Запрошено устройство 'cuda', но CUDA не доступна на этой системе. Тест будет пропущен.")
            return None

        if device_str in ('mps', 'metal'):
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return DeviceType.MPS
            logger.warning("⚠️ Запрошено устройство 'mps', но MPS не доступен на этой системе. Тест будет пропущен.")
            return None

        if device_str in ('npu', 'gpu', 'tpu', 'tensorrt', 'npu:rk3588', 'npu:intel', 'npu:hailo', 'tpu:coral'):
            logger.warning(f"⚠️ Устройство '{device_str}' не поддерживается напрямую в этом окружении. Тест будет пропущен.")
            return None

        if device_str == 'cpu':
            return DeviceType.CPU

        logger.warning(f"⚠️ Неизвестное устройство '{device_str}'. Тест будет пропущен.")
        return None

    def _cleanup_model_resources(self, model: YOLOBackend | None) -> None:
        if model is None:
            return
        raw_model = getattr(model, "model", None)
        self._call_cleanup_method(model)
        self._call_cleanup_method(raw_model)
        predictor = getattr(raw_model, "predictor", None)
        if predictor is not None:
            self._clear_predictor_resources(predictor)
        self._clear_torch_caches()
        self._destroy_cv2_windows()
        gc.collect()

    def _call_cleanup_method(self, value: object | None) -> None:
        if value is None:
            return
        for method_name in ("close", "release"):
            method = getattr(value, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception as error:
                    logger.debug("Не удалось вызвать %s(): %s", method_name, error)

    def _clear_predictor_resources(self, predictor: object) -> None:
        for attribute_name in ("dataset", "vid_writer", "plotted_img", "results", "batch"):
            try:
                setattr(predictor, attribute_name, None)
            except Exception as error:
                logger.debug("Не удалось очистить predictor.%s: %s", attribute_name, error)

    def _clear_torch_caches(self) -> None:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            try:
                torch.cuda.ipc_collect()
            except Exception as error:
                logger.debug("Не удалось очистить CUDA IPC cache: %s", error)
        if hasattr(torch, "mps") and torch.backends.mps.is_available():
            try:
                torch.mps.empty_cache()
            except Exception as error:
                logger.debug("Не удалось очистить MPS cache: %s", error)

    def _destroy_cv2_windows(self) -> None:
        try:
            cv2.destroyAllWindows()
        except Exception as error:
            logger.debug("Не удалось закрыть окна OpenCV: %s", error)

    def _collect_quality_metrics(self, model: YOLOBackend, family: str, size: str) -> QualityMetrics | None:
        try:
            dataset_config_path = self._find_quality_dataset_config()
            if dataset_config_path is None:
                logger.debug("Датасет с разметкой не найден для %s%s, пропускаю сбор метрик качества", family, size)
                return None
            logger.info("Собираю метрики качества для %s%s на датасете: %s", family, size, dataset_config_path)
            collector = YOLOQualityMetricsCollector(
                yolo_backend=model, dataset_path=dataset_config_path, task_type=self._get_task_type(),
                imgsz=self.benchmark_config.input_size or 640,
                conf_threshold=self.benchmark_config.confidence_threshold or 0.25,
            )
            return collector.collect()
        except Exception as e:
            logger.warning("Не удалось собрать метрики качества для %s%s: %s", family, size, e)
            return None

    def _find_quality_dataset_config(self) -> Path | None:
        validation_paths: list[Path] = []
        if self.benchmark_config.test_images is not None:
            benchmark_dataset_path = Path(self.benchmark_config.test_images)
            validation_paths.extend([benchmark_dataset_path / "data.yaml", benchmark_dataset_path.parent / "data.yaml"])
        validation_paths.extend([
            Path("dataset/data.yaml"), Path("dataset/val/data.yaml"), Path("dataset/validation/data.yaml"),
            Path("dataset/coco/data.yaml"), Path("data/val/data.yaml"),
        ])
        for path in validation_paths:
            if path.is_file():
                return path
        return None

    def _warmup(self, backend: Backend) -> None:
        input_size = self.benchmark_config.input_size or 640
        warmup_iterations = self.benchmark_config.warmup_iterations or 10
        fake_frame = np.zeros((input_size, input_size, 3), dtype=np.uint8)
        for _ in range(warmup_iterations):
            backend.predict(fake_frame)


