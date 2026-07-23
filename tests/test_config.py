# tests/test_config.py

import logging
import tempfile
import unittest
from pathlib import Path

from ddt import data, ddt, unpack

from core.entities.config import (
    BenchmarkConfig,
    BenchmarkRun,
    Config,
    ModelConfig,
    OutputConfig,
    SystemInfoConfig,
    to_plain_dict,
)
from core.enums.model import DeviceType, QuantizationLevel, TaskType
from infrastructure.config.config_reader import read_yaml
from infrastructure.config.configs_validator import ConfigError

logger = logging.getLogger(__name__)


@ddt
class TestModelConfig(unittest.TestCase):
    """Тесты для ModelConfig."""

    def test_init_success(self) -> None:
        """Успешная инициализация"""
        model = ModelConfig(family="yolov8", size="n")
        self.assertEqual(model.family, "yolov8")
        self.assertEqual(model.size, "n")

    def test_name_property(self) -> None:
        """Проверка свойства name, которое объединяет family и size"""
        model = ModelConfig(family="yolov8", size="n")
        self.assertEqual(model.name, "yolov8-n")

    def test_frozen(self) -> None:
        """Проверка на неизменяемость"""
        model = ModelConfig(family="yolov8", size="n")
        with self.assertRaises(AttributeError):
            model.family = "yolov11"

    def test_to_dict(self) -> None:
        """Сериализация в словарь"""
        model = ModelConfig(family="yolov10", size="s")
        result = model.to_dict()
        self.assertEqual(result, {"family": "yolov10", "size": "s"})


@ddt
class TestBenchmarkRun(unittest.TestCase):
    """Тесты для BenchmarkRun"""

    def test_init_single_model(self) -> None:
        """Инициализация с одной моделью"""
        model = ModelConfig(family="yolov8", size="n")
        run = BenchmarkRun(models=(model,))
        self.assertEqual(run.model_names, ("yolov8-n",))

    def test_init_multiple_models(self) -> None:
        """Инициализация с несколькими моделями"""
        models = (
            ModelConfig(family="yolov8", size="n"),
            ModelConfig(family="yolov11", size="s"),
        )
        run = BenchmarkRun(models=models)
        self.assertEqual(run.model_names, ("yolov8-n", "yolov11-s"))

    def test_init_empty_models(self) -> None:
        """Пустой кортеж моделей допустим"""
        run = BenchmarkRun(models=())
        self.assertEqual(run.model_names, ())

    def test_to_dict(self) -> None:
        """Сериализация в словарь"""
        model = ModelConfig(family="yolov8", size="n")
        run = BenchmarkRun(models=(model,))
        result = run.to_dict()
        self.assertEqual(result["models"], [{"family": "yolov8", "size": "n"}])

    def test_frozen(self) -> None:
        """Проверка на неизменяемость"""
        run = BenchmarkRun(models=())
        with self.assertRaises(AttributeError):
            run.models = (ModelConfig(family="yolov8", size="n"),)


@ddt
class TestBenchmarkConfig(unittest.TestCase):
    """Тесты для BenchmarkConfig"""

    @staticmethod
    def _make_run() -> BenchmarkRun:
        """Создать конфиг запуска"""
        return BenchmarkRun(models=(ModelConfig(family="yolov8", size="n"),))

    def test_init_minimal(self) -> None:
        """Минимальная инициализация только с runs"""
        run = self._make_run()
        config = BenchmarkConfig(runs=(run,))
        self.assertEqual(len(config.runs), 1)
        self.assertEqual(config.formats, ())
        self.assertIsNone(config.input_size)

    def test_init_full(self) -> None:
        """Полная инициализация со всеми параметрами"""
        run = self._make_run()
        config = BenchmarkConfig(
            runs=(run,),
            formats=("pytorch", "onnx"),
            quantization=("fp32", "fp16"),
            task_type=TaskType.SEGMENT,
            device_type=DeviceType.CPU,
            input_size=640,
            batch_size=1,
            warmup_iterations=10,
            main_iterations=100,
            confidence_threshold=0.25,
            test_images="./data/test_images",
        )
        self.assertEqual(config.input_size, 640)
        self.assertEqual(config.batch_size, 1)
        self.assertEqual(config.confidence_threshold, 0.25)
        self.assertEqual(config.quantization, ("fp32", "fp16"))
        self.assertEqual(config.task_type, TaskType.SEGMENT)

    def test_to_dict(self) -> None:
        """Сериализация в словарь"""
        run = self._make_run()
        config = BenchmarkConfig(
            runs=(run,),
            formats=("pytorch",),
            quantization=("fp32",),
            task_type=TaskType.DETECT,
            input_size=640,
        )
        result = config.to_dict()
        self.assertEqual(result["input_size"], 640)
        self.assertEqual(result["formats"], ["pytorch"])
        self.assertEqual(result["quantization"], ["fp32"])
        self.assertEqual(result["task_type"], TaskType.DETECT.value)


@ddt
class TestSystemInfoConfig(unittest.TestCase):
    """Тесты для SystemInfoConfig."""

    @data(
        (True, False, True),
        (False, True, False),
        (True, True, True),
    )
    @unpack
    def test_init(self, gpu: bool, power: bool, temp: bool) -> None:
        """Инициализация с различными комбинациями флагов"""
        config = SystemInfoConfig(
            collect_gpu=gpu,
            collect_power=power,
            collect_temperature=temp,
        )
        self.assertEqual(config.collect_gpu, gpu)
        self.assertEqual(config.collect_power, power)
        self.assertEqual(config.collect_temperature, temp)

    def test_to_dict(self) -> None:
        """Сериализация в словарь"""
        config = SystemInfoConfig(
            collect_gpu=False,
            collect_power=True,
            collect_temperature=False,
        )
        result = config.to_dict()
        self.assertEqual(
            result,
            {"collect_gpu": False, "collect_power": True, "collect_temperature": False},
        )

    def test_frozen(self) -> None:
        """Проверка на неизменяемость"""
        config = SystemInfoConfig(collect_gpu=True, collect_power=True, collect_temperature=True)
        with self.assertRaises(AttributeError):
            config.collect_gpu = False


@ddt
class TestOutputConfig(unittest.TestCase):
    """Тесты для OutputConfig"""

    def test_init(self) -> None:
        """Успешная инициализация"""
        output = OutputConfig(
            directory=Path("./results"),
            formats=("json", "csv"),
            use_timestamp=True,
        )
        self.assertEqual(output.directory, Path("./results"))
        self.assertEqual(output.formats, ("json", "csv"))
        self.assertTrue(output.use_timestamp)

    @data(
        (Path("./results"), ("json",), True),
        (Path("/tmp"), ("csv",), False),
        (Path("results"), (), False),
    )
    @unpack
    def test_init_variations(self, path: Path, formats: tuple, timestamp: bool) -> None:
        """Различные комбинации параметров"""
        output = OutputConfig(
            directory=path,
            formats=formats,
            use_timestamp=timestamp,
        )
        self.assertEqual(output.directory, path)
        self.assertEqual(output.formats, formats)
        self.assertEqual(output.use_timestamp, timestamp)

    def test_to_dict(self) -> None:
        """Сериализация в словарь"""
        output = OutputConfig(
            directory=Path("./results"),
            formats=("json", "csv"),
            use_timestamp=True,
        )
        result = output.to_dict()
        # Path преобразуется в нормализованную строку
        self.assertIsInstance(result["directory"], str)
        self.assertEqual(result["formats"], ["json", "csv"])
        self.assertTrue(result["use_timestamp"])


@ddt
class TestConfig(unittest.TestCase):
    """Тесты для Config"""

    @staticmethod
    def _make_benchmark() -> BenchmarkConfig:
        """Создает бенчмарк конфиг"""
        run = BenchmarkRun(models=(ModelConfig(family="yolov8", size="n"),))
        return BenchmarkConfig(runs=(run,), formats=("pytorch",), input_size=640)

    @staticmethod
    def _make_system_info() -> SystemInfoConfig:
        """Создает конфиг системной информации"""
        return SystemInfoConfig(collect_gpu=True, collect_power=False, collect_temperature=True)

    @staticmethod
    def _make_output() -> OutputConfig:
        """Создает конфиг вывода"""
        return OutputConfig(
            directory=Path("./results"),
            formats=("json",),
            use_timestamp=True,
        )

    def test_init_full(self) -> None:
        """Полная инициализация"""
        config = Config(
            benchmark=self._make_benchmark(),
            system_info=self._make_system_info(),
            output=self._make_output(),
        )
        self.assertIsNotNone(config.benchmark)
        self.assertIsNotNone(config.system_info)
        self.assertEqual(config.output.use_timestamp, True)

    def test_init_no_benchmark(self) -> None:
        """Инициализация без бенчмарка"""
        config = Config(
            benchmark=None,
            system_info=self._make_system_info(),
            output=self._make_output(),
        )
        self.assertIsNone(config.benchmark)

    def test_init_no_system_info(self) -> None:
        """Инициализация без информации о системе"""
        config = Config(
            benchmark=self._make_benchmark(),
            system_info=None,
            output=self._make_output(),
        )
        self.assertIsNone(config.system_info)

    def test_frozen(self) -> None:
        """Проверка на неизменяемость"""
        config = Config(
            benchmark=self._make_benchmark(),
            system_info=self._make_system_info(),
            output=self._make_output(),
        )
        with self.assertRaises(AttributeError):
            config.benchmark = None

    def test_to_dict(self) -> None:
        """Сериализация в словарь"""
        config = Config(
            benchmark=self._make_benchmark(),
            system_info=self._make_system_info(),
            output=self._make_output(),
        )
        result = config.to_dict()
        self.assertEqual(result["benchmark"]["input_size"], 640)
        self.assertEqual(result["output"]["use_timestamp"], True)


@ddt
class TestToPlainDict(unittest.TestCase):
    """Тесты для функции to_plain_dict"""

    def test_primitives(self) -> None:
        """Примитивные типы остаются без изменений"""
        self.assertEqual(to_plain_dict(42), 42)
        self.assertEqual(to_plain_dict("text"), "text")
        self.assertEqual(to_plain_dict(3.14), 3.14)
        self.assertIsNone(to_plain_dict(None))

    def test_list(self) -> None:
        """Списки обрабатываются рекурсивно"""
        result = to_plain_dict([1, 2, 3])
        self.assertEqual(result, [1, 2, 3])

    def test_tuple(self) -> None:
        """Кортежи преобразуются в списки"""
        result = to_plain_dict((1, 2, 3))
        self.assertEqual(result, [1, 2, 3])

    def test_dict(self) -> None:
        """Словари обрабатываются рекурсивно"""
        result = to_plain_dict({"a": 1, "b": 2})
        self.assertEqual(result, {"a": 1, "b": 2})

    def test_dataclass(self) -> None:
        """Dataclass преобразуется в словарь"""
        model = ModelConfig(family="yolov8", size="n")
        result = to_plain_dict(model)
        self.assertEqual(result, {"family": "yolov8", "size": "n"})

    def test_nested_structures(self) -> None:
        """Вложенные структуры обрабатываются рекурсивно"""
        model = ModelConfig(family="yolov8", size="n")
        run = BenchmarkRun(models=(model,))
        result = to_plain_dict(run)
        self.assertEqual(
            result,
            {"models": [{"family": "yolov8", "size": "n"}]},
        )


@ddt
class TestReadYaml(unittest.TestCase):
    """Тесты для функции read_yaml"""

    def test_valid_yaml(self) -> None:
        """Загрузка корректного YAML файла"""
        yaml_content = """
        benchmark:
          runs:
            - models:
                - family: yolov8
                  sizes: [n]
          formats:
            - pytorch
            - onnx
          quantization:
            - fp32
            - fp16
          task_type: segment
          device_type: cuda
          input_size: 640
          batch_size: 1
        output:
          directory: ./results
          formats:
            - json
            - csv
          timestamp: true
        system_info:
          collect_gpu: true
          collect_power: false
          collect_temperature: true
        """
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            config = read_yaml(temp_path)
            self.assertIsNotNone(config.benchmark)
            self.assertEqual(config.benchmark.input_size, 640)
            self.assertEqual(config.benchmark.device_type, DeviceType.CUDA)
            self.assertEqual(
                config.benchmark.quantization,
                (QuantizationLevel.FP32.value, QuantizationLevel.FP16.value),
            )
            self.assertEqual(config.benchmark.task_type, TaskType.SEGMENT)
            self.assertTrue(config.system_info.collect_gpu)
            self.assertFalse(config.system_info.collect_power)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_yaml_without_benchmark(self) -> None:
        """YAML без секции benchmark допустим"""
        yaml_content = """
        output:
          directory: ./results
          formats:
            - json
          timestamp: false
        """
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            config = read_yaml(temp_path)
            self.assertIsNone(config.benchmark)
            self.assertIsNotNone(config.output)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_yaml_without_system_info(self) -> None:
        """YAML без секции system_info допустим"""
        yaml_content = """
        output:
          directory: ./results
          formats:
            - json
          timestamp: false
        """
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            config = read_yaml(temp_path)
            self.assertIsNone(config.system_info)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_yaml_without_quantization_uses_fp32(self) -> None:
        """Если quantization не задан, используется базовый fp32."""
        yaml_content = """
        benchmark:
          runs:
            - models:
                - family: yolov8
                  sizes: [n]
          formats:
            - pytorch
        output:
          directory: ./results
          formats:
            - json
          timestamp: false
        """
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            config = read_yaml(temp_path)
            self.assertIsNotNone(config.benchmark)
            self.assertEqual(config.benchmark.quantization, (QuantizationLevel.FP32.value,))
            self.assertEqual(config.benchmark.task_type, TaskType.DETECT)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_invalid_task_type_is_rejected(self) -> None:
        """Некорректный task_type должен валидироваться как ошибка."""
        yaml_content = """
        benchmark:
          runs:
            - models:
                - family: yolov8
                  sizes: [n]
          formats:
            - pytorch
          task_type: unknown_task
        output:
          directory: ./results
          formats:
            - json
          timestamp: false
        """
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ConfigError):
                read_yaml(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_model_with_size_is_rejected(self) -> None:
        """Конфиг с полем size должен валидироваться как ошибка."""
        yaml_content = """
        benchmark:
          runs:
            - models:
                - family: llama
                  size: 7b
        output:
          directory: ./results
          formats:
            - json
          timestamp: false
        """
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ConfigError):
                read_yaml(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_missing_output_section(self) -> None:
        """Отсутствие output вызывает ошибку"""
        yaml_content = """
        benchmark:
          runs:
            - models:
                - family: yolov8
                  sizes: [n]
        """
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ConfigError):
                read_yaml(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_missing_file(self) -> None:
        """Несуществующий файл вызывает ошибку"""
        with self.assertRaises(FileNotFoundError):
            read_yaml(Path("nonexistent.yaml"))

    def test_invalid_yaml(self) -> None:
        """Неправильный YAML вызывает ошибку"""
        yaml_content = "benchmark: ["
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ConfigError):
                read_yaml(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_yaml_root_not_dict(self) -> None:
        """Корень YAML должен быть словарём"""
        yaml_content = "[1, 2, 3]"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ConfigError):
                read_yaml(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_path_as_string(self) -> None:
        """Функция принимает путь как строку или Path"""
        yaml_content = """
        output:
          directory: ./results
          formats:
            - json
          timestamp: false
        """
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = read_yaml(temp_path)
            self.assertIsNotNone(config.output)
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
