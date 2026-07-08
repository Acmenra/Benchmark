import tempfile
import unittest
from pathlib import Path
from typing import Any

from ddt import data, ddt, unpack

from configs.config import (
    BenchmarkConfig,
    BenchmarkRun,
    Config,
    ConfigError,
    ModelConfig,
    OutputConfig,
    SystemInfoConfig,
    read_yaml,
)


@ddt
class TestModelConfig(unittest.TestCase):
    """Unit tests for the ModelConfig class."""

    def test_model_config_initialisation_success(self) -> None:
        """
        Test successful initialization of ModelConfig with valid values.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The created object is an instance of ModelConfig.
        - The family, size, and full model name are stored correctly.
        """
        model = ModelConfig(family="yolov8", size="n")

        self.assertIsInstance(model, ModelConfig)
        self.assertEqual(model.family, "yolov8")
        self.assertEqual(model.size, "n")
        self.assertEqual(model.name, "yolov8n")

    @data(-1, 1.5, True, None, [], {})
    def test_model_config_family_setter_wrong_type(self, value: Any) -> None:
        """
        Test invalid family values for the ModelConfig setter.

        Parameters:
        -----------
        value : Any
            An invalid value assigned to the family attribute.

        Asserts:
        --------
        - A TypeError is raised for unsupported non-string values.
        """
        model = ModelConfig(family="yolov8", size="n")

        with self.assertRaises(TypeError):
            model.family = value

    @data("", "  ")
    def test_model_config_family_setter_wrong_value(self, value: str) -> None:
        """
        Test unsupported or empty family values for the ModelConfig setter.

        Parameters:
        -----------
        value : str
            An invalid family string value.

        Asserts:
        --------
        - A ConfigError is raised for empty or invalid family values.
        """
        model = ModelConfig(family="yolov8", size="n")

        with self.assertRaises(ConfigError):
            model.family = value

    @data(-1, 1.5, True, None, [], {})
    def test_model_config_size_setter_wrong_type(self, value: Any) -> None:
        """
        Test invalid size values for the ModelConfig setter.

        Parameters:
        -----------
        value : Any
            An invalid value assigned to the size attribute.

        Asserts:
        --------
        - A TypeError is raised for unsupported non-string values.
        """
        model = ModelConfig(family="yolov8", size="n")

        with self.assertRaises(TypeError):
            model.size = value

    @data("z", "", "  ")
    def test_model_config_size_setter_wrong_value(self, value: str) -> None:
        """
        Test unsupported or empty size values for the ModelConfig setter.

        Parameters:
        -----------
        value : str
            An invalid size string value.

        Asserts:
        --------
        - A ConfigError is raised for unsupported or empty size values.
        """
        model = ModelConfig(family="yolov8", size="n")

        with self.assertRaises(ConfigError):
            model.size = value

    def test_model_config_to_dict_success(self) -> None:
        """
        Test serialization of ModelConfig to a dictionary.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The serialized result contains family, size, and name values.
        """
        model = ModelConfig(family="yolov11", size="m")

        result = model.to_dict()

        self.assertEqual(result, {"family": "yolov11", "size": "m", "name": "yolov11m"})

    def test_model_config_from_dict_success(self) -> None:
        """
        Test construction of ModelConfig from a dictionary.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The object is created successfully.
        - The resulting full model name matches the input data.
        """
        model = ModelConfig.from_dict({"family": "yolov10", "size": "s"})

        self.assertIsInstance(model, ModelConfig)
        self.assertEqual(model.name, "yolov10s")

    def test_model_config_from_dict_wrong_value(self) -> None:
        """
        Test ModelConfig.from_dict with a multi-size definition.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - A ConfigError is raised when a multi-size definition is passed.
        """
        with self.assertRaises(ConfigError):
            ModelConfig.from_dict({"family": "yolov8", "size": "n", "sizes": ["n", "s"]})


@ddt
class TestBenchmarkRun(unittest.TestCase):
    """Unit tests for the BenchmarkRun class."""

    def test_benchmark_run_initialisation_success(self) -> None:
        """
        Test successful initialization of BenchmarkRun with valid models.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The benchmark run is created successfully.
        - The aggregated model names contain the expected values.
        """
        model = ModelConfig(family="yolov8", size="n")
        run = BenchmarkRun(models=[model])

        self.assertIsInstance(run, BenchmarkRun)
        self.assertEqual(run.model_names, ["yolov8n"])

    @data(["not", "a", "model"], "yolov8", None, [])
    def test_benchmark_run_models_setter_wrong_type(self, value: Any) -> None:
        """
        Test invalid values for the models setter.

        Parameters:
        -----------
        value : Any
            An invalid value passed to the models argument.

        Asserts:
        --------
        - A TypeError or ConfigError is raised for invalid model collections.
        """
        with self.assertRaises((TypeError, ConfigError)):
            BenchmarkRun(models=value)

    def test_benchmark_run_models_setter_duplicate_models(self) -> None:
        """
        Test duplicate models in a benchmark run.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - A ConfigError is raised when duplicate model variants are provided.
        """
        duplicate_models = [ModelConfig(family="yolov8", size="n"), ModelConfig(family="yolov8", size="n")]

        with self.assertRaises(ConfigError):
            BenchmarkRun(models=duplicate_models)

    def test_benchmark_run_to_dict_success(self) -> None:
        """
        Test serialization of BenchmarkRun to a dictionary.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The serialized result contains the expected model dictionary.
        """
        run = BenchmarkRun(models=[ModelConfig(family="yolov8", size="n")])

        result = run.to_dict()

        self.assertEqual(result, {"models": [{"family": "yolov8", "size": "n", "name": "yolov8n"}]})

    def test_benchmark_run_from_dict_single_model_with_sizes(self) -> None:
        """
        Test expansion of a single model definition with multiple sizes.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The single model entry expands into separate ModelConfig values for each size.
        """
        run = BenchmarkRun.from_dict({"models": [{"family": "yolov8", "sizes": ["n", "s", "m"]}]})

        self.assertEqual(run.model_names, ["yolov8n", "yolov8s", "yolov8m"])

    def test_benchmark_run_from_dict_multiple_models(self) -> None:
        """
        Test parsing of several model definitions with one size each.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - Each model definition is parsed into the expected full model names.
        """
        run = BenchmarkRun.from_dict({"models": [{"family": "yolov11", "size": "n"}, {"family": "yolov12", "size": "s"}]})

        self.assertEqual(run.model_names, ["yolov11n", "yolov12s"])


@ddt
class TestBenchmarkConfig(unittest.TestCase):
    """Unit tests for the BenchmarkConfig class."""

    @staticmethod
    def _build_benchmark_config() -> BenchmarkConfig:
        """Create a valid benchmark configuration for reuse in tests."""
        return BenchmarkConfig(
            runs=[BenchmarkRun(models=[ModelConfig(family="yolov8", size="n")])],
            formats=["pytorch", "onnx"],
            input_size=640,
            batch_size=1,
            warmup_iterations=10,
            main_iterations=100,
            confidence_threshold=0.25,
            test_images=Path("./data/test_images"),
        )

    def test_benchmark_config_initialisation_success(self) -> None:
        """
        Test successful initialization of BenchmarkConfig with valid values.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The object is created successfully.
        - The input size and format list are stored as expected.
        """
        config = self._build_benchmark_config()

        self.assertIsInstance(config, BenchmarkConfig)
        self.assertEqual(config.input_size, 640)
        self.assertEqual(config.formats, ["pytorch", "onnx"])

    @data(["not", "valid"], None, [])
    def test_benchmark_config_runs_setter_wrong_type(self, value: Any) -> None:
        """
        Test invalid values for the runs setter.

        Parameters:
        -----------
        value : Any
            An invalid value passed as the runs argument.

        Asserts:
        --------
        - A TypeError or ConfigError is raised for invalid run collections.
        """
        with self.assertRaises((TypeError, ConfigError)):
            BenchmarkConfig(
                runs=value,
                formats=["pytorch"],
                input_size=640,
                batch_size=1,
                warmup_iterations=10,
                main_iterations=100,
                confidence_threshold=0.25,
                test_images=Path("./data/test_images"),
            )

    @data(["invalid", "format"], ["pytorch", "pytorch"], [])
    def test_benchmark_config_formats_setter_wrong_value(self, value: Any) -> None:
        """
        Test invalid benchmark format lists.

        Parameters:
        -----------
        value : Any
            An invalid list of benchmark formats.

        Asserts:
        --------
        - A TypeError or ConfigError is raised for unsupported format values.
        """
        with self.assertRaises((TypeError, ConfigError)):
            BenchmarkConfig(
                runs=[BenchmarkRun(models=[ModelConfig(family="yolov8", size="n")])],
                formats=value,
                input_size=640,
                batch_size=1,
                warmup_iterations=10,
                main_iterations=100,
                confidence_threshold=0.25,
                test_images=Path("./data/test_images"),
            )

    @data(0, -1, True)
    def test_benchmark_config_positive_int_setter_wrong_value(self, value: Any) -> None:
        """
        Test validation of positive integer fields.

        Parameters:
        -----------
        value : Any
            An invalid input size value.

        Asserts:
        --------
        - A TypeError or ConfigError is raised for non-positive integers.
        """
        with self.assertRaises((TypeError, ConfigError)):
            BenchmarkConfig(
                runs=[BenchmarkRun(models=[ModelConfig(family="yolov8", size="n")])],
                formats=["pytorch"],
                input_size=value,
                batch_size=1,
                warmup_iterations=10,
                main_iterations=100,
                confidence_threshold=0.25,
                test_images=Path("./data/test_images"),
            )

    @data(-1, True)
    def test_benchmark_config_non_negative_int_setter_wrong_value(self, value: Any) -> None:
        """
        Test validation of non-negative integer fields.

        Parameters:
        -----------
        value : Any
            An invalid warmup iteration value.

        Asserts:
        --------
        - A TypeError or ConfigError is raised for negative or invalid integers.
        """
        with self.assertRaises((TypeError, ConfigError)):
            BenchmarkConfig(
                runs=[BenchmarkRun(models=[ModelConfig(family="yolov8", size="n")])],
                formats=["pytorch"],
                input_size=640,
                batch_size=1,
                warmup_iterations=value,
                main_iterations=100,
                confidence_threshold=0.25,
                test_images=Path("./data/test_images"),
            )

    @data(-0.1, 1.1, True, None)
    def test_benchmark_config_confidence_threshold_wrong_value(self, value: Any) -> None:
        """
        Test validation of the confidence threshold field.

        Parameters:
        -----------
        value : Any
            An invalid confidence threshold value.

        Asserts:
        --------
        - A TypeError or ConfigError is raised for out-of-range values.
        """
        with self.assertRaises((TypeError, ConfigError)):
            BenchmarkConfig(
                runs=[BenchmarkRun(models=[ModelConfig(family="yolov8", size="n")])],
                formats=["pytorch"],
                input_size=640,
                batch_size=1,
                warmup_iterations=10,
                main_iterations=100,
                confidence_threshold=value,
                test_images=Path("./data/test_images"),
            )

    def test_benchmark_config_model_names_property(self) -> None:
        """
        Test the aggregated model names property.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The property returns the expected list of model names.
        """
        config = self._build_benchmark_config()

        self.assertEqual(config.model_names, ["yolov8n"])

    def test_benchmark_config_to_dict_success(self) -> None:
        """
        Test serialization of BenchmarkConfig to a dictionary.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The serialized output contains the expected benchmark values.
        """
        config = self._build_benchmark_config()

        result = config.to_dict()

        self.assertEqual(result["input_size"], 640)
        self.assertEqual(result["formats"], ["pytorch", "onnx"])
        self.assertEqual(result["runs"][0]["models"][0]["name"], "yolov8n")

    def test_benchmark_config_from_dict_success(self) -> None:
        """
        Test creation of BenchmarkConfig from a dictionary.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The benchmark configuration is created successfully.
        - The expanded model names match the expected values.
        """
        data = {
            "runs": [{"models": [{"family": "yolov8", "sizes": ["n", "s"]}]}],
            "formats": ["pytorch", "onnx"],
            "input_size": 640,
            "batch_size": 1,
            "warmup_iterations": 10,
            "main_iterations": 100,
            "confidence_threshold": 0.25,
            "test_images": "./data/test_images",
        }

        config = BenchmarkConfig.from_dict(data=data)

        self.assertEqual(config.model_names, ["yolov8n", "yolov8s"])


@ddt
class TestSystemInfoConfig(unittest.TestCase):
    """Unit tests for the SystemInfoConfig class."""

    def test_system_info_config_initialisation_success(self) -> None:
        """
        Test successful initialization of SystemInfoConfig.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The object stores the provided boolean values correctly.
        """
        system_info = SystemInfoConfig(collect_gpu=True, collect_power=False, collect_temperature=True)

        self.assertTrue(system_info.collect_gpu)
        self.assertFalse(system_info.collect_power)
        self.assertTrue(system_info.collect_temperature)

    @data(True, False)
    def test_system_info_config_collect_gpu_setter(self, value: Any) -> None:
        """
        Test the collect_gpu setter with valid boolean values.

        Parameters:
        -----------
        value : Any
            A boolean value assigned to collect_gpu.

        Asserts:
        --------
        - The stored value matches the input boolean.
        """
        system_info = SystemInfoConfig(collect_gpu=True, collect_power=True, collect_temperature=True)
        system_info.collect_gpu = value
        self.assertEqual(system_info.collect_gpu, value)

    @data("yes", 1, None)
    def test_system_info_config_collect_gpu_setter_wrong_type(self, value: Any) -> None:
        """
        Test invalid values for the collect_gpu setter.

        Parameters:
        -----------
        value : Any
            An invalid value assigned to collect_gpu.

        Asserts:
        --------
        - A TypeError is raised for non-boolean values.
        """
        system_info = SystemInfoConfig(collect_gpu=True, collect_power=True, collect_temperature=True)
        with self.assertRaises(TypeError):
            system_info.collect_gpu = value

    def test_system_info_config_to_dict_success(self) -> None:
        """
        Test serialization of SystemInfoConfig to a dictionary.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The serialized dictionary matches the expected booleans.
        """
        system_info = SystemInfoConfig(collect_gpu=False, collect_power=True, collect_temperature=False)

        result = system_info.to_dict()

        self.assertEqual(result, {"collect_gpu": False, "collect_power": True, "collect_temperature": False})

    def test_system_info_config_from_dict_success(self) -> None:
        """
        Test construction of SystemInfoConfig from a dictionary.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The object is built successfully.
        - The boolean fields are read correctly from the input dictionary.
        """
        system_info = SystemInfoConfig.from_dict({"collect_gpu": False, "collect_power": True, "collect_temperature": True})

        self.assertFalse(system_info.collect_gpu)
        self.assertTrue(system_info.collect_power)
        self.assertTrue(system_info.collect_temperature)

    def test_system_info_config_from_dict_none(self) -> None:
        """
        Test default values when from_dict receives None.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - Default values are applied for all boolean flags.
        """
        system_info = SystemInfoConfig.from_dict(None)

        self.assertTrue(system_info.collect_gpu)
        self.assertTrue(system_info.collect_power)
        self.assertTrue(system_info.collect_temperature)


@ddt
class TestOutputConfig(unittest.TestCase):
    """Unit tests for the OutputConfig class."""

    def test_output_config_initialisation_success(self) -> None:
        """
        Test successful initialization of OutputConfig.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The directory, formats, and timestamp flag are stored correctly.
        """
        output = OutputConfig(directory=Path("./results"), formats=["json", "csv"], use_timestamp=True)

        self.assertEqual(output.directory, Path("./results"))
        self.assertEqual(output.formats, ["json", "csv"])
        self.assertTrue(output.use_timestamp)

    @data("./results", 1, None)
    def test_output_config_directory_setter_wrong_type(self, value: Any) -> None:
        """
        Test invalid values for the directory setter.

        Parameters:
        -----------
        value : Any
            An invalid value assigned to the directory attribute.

        Asserts:
        --------
        - A TypeError is raised for non-Path values.
        """
        output = OutputConfig(directory=Path("./results"), formats=["json"], use_timestamp=True)
        with self.assertRaises(TypeError):
            output.directory = value

    @data(["invalid"], ["json", "json"], [])
    def test_output_config_formats_setter_wrong_value(self, value: Any) -> None:
        """
        Test invalid output format lists.

        Parameters:
        -----------
        value : Any
            An invalid output format list.

        Asserts:
        --------
        - A TypeError or ConfigError is raised for unsupported format values.
        """
        output = OutputConfig(directory=Path("./results"), formats=["json"], use_timestamp=True)
        with self.assertRaises((TypeError, ConfigError)):
            output.formats = value

    @data("yes", 1, None)
    def test_output_config_use_timestamp_setter_wrong_type(self, value: Any) -> None:
        """
        Test invalid values for the use_timestamp setter.

        Parameters:
        -----------
        value : Any
            An invalid value assigned to the timestamp flag.

        Asserts:
        --------
        - A TypeError is raised for non-boolean values.
        """
        output = OutputConfig(directory=Path("./results"), formats=["json"], use_timestamp=True)
        with self.assertRaises(TypeError):
            output.use_timestamp = value

    def test_output_config_to_dict_success(self) -> None:
        """
        Test serialization of OutputConfig to a dictionary.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The serialized dictionary contains the expected directory, formats, and timestamp flag.
        """
        output = OutputConfig(directory=Path("./results"), formats=["md", "json"], use_timestamp=False)

        result = output.to_dict()

        self.assertEqual(result["directory"], str(Path("./results")))
        self.assertEqual(result["formats"], ["markdown", "json"])
        self.assertFalse(result["timestamp"])

    def test_output_config_from_dict_success(self) -> None:
        """
        Test construction of OutputConfig from a dictionary.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The object is created successfully.
        - The directory, formats, and timestamp values are parsed correctly.
        """
        output = OutputConfig.from_dict({"directory": "./results", "formats": ["json", "csv"], "timestamp": True})

        self.assertEqual(output.directory, Path("./results"))
        self.assertEqual(output.formats, ["json", "csv"])
        self.assertTrue(output.use_timestamp)


@ddt
class TestConfig(unittest.TestCase):
    """Unit tests for the Config class."""

    def test_config_initialisation_success(self) -> None:
        """
        Test successful initialization of the root Config object.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The root configuration stores benchmark, system information, output, and source path correctly.
        """
        config = Config(
            benchmark=BenchmarkConfig(
                runs=[BenchmarkRun(models=[ModelConfig(family="yolov8", size="n")])],
                formats=["pytorch"],
                input_size=640,
                batch_size=1,
                warmup_iterations=10,
                main_iterations=100,
                confidence_threshold=0.25,
                test_images=Path("./data/test_images"),
            ),
            system_info=SystemInfoConfig(collect_gpu=True, collect_power=False, collect_temperature=True),
            output=OutputConfig(directory=Path("./results"), formats=["json"], use_timestamp=True),
            source_path=Path("./test_config.yaml"),
        )

        self.assertEqual(config.benchmark.input_size, 640)
        self.assertTrue(config.system_info.collect_gpu)
        self.assertEqual(config.output.formats, ["json"])
        self.assertEqual(config.source_path, Path("./test_config.yaml"))

    def test_config_to_dict_success(self) -> None:
        """
        Test serialization of the root Config object.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The serialized dictionary contains the expected benchmark, output, and source path data.
        """
        config = Config(
            benchmark=BenchmarkConfig(
                runs=[BenchmarkRun(models=[ModelConfig(family="yolov8", size="n")])],
                formats=["pytorch"],
                input_size=640,
                batch_size=1,
                warmup_iterations=10,
                main_iterations=100,
                confidence_threshold=0.25,
                test_images=Path("./data/test_images"),
            ),
            system_info=SystemInfoConfig(collect_gpu=True, collect_power=False, collect_temperature=True),
            output=OutputConfig(directory=Path("./results"), formats=["json"], use_timestamp=True),
            source_path=Path("./test_config.yaml"),
        )

        result = config.to_dict()

        self.assertEqual(result["benchmark"]["input_size"], 640)
        self.assertEqual(result["output"]["directory"], str(Path("./results")))
        self.assertEqual(result["source_path"], str(Path("./test_config.yaml")))

    def test_config_from_dict_success(self) -> None:
        """
        Test construction of Config from a dictionary.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The root configuration is built successfully.
        - The benchmark model names and system info flags are parsed correctly.
        """
        data = {
            "benchmark": {
                "runs": [{"models": [{"family": "yolov8", "sizes": ["n", "s"]}]}],
                "formats": ["pytorch"],
                "input_size": 640,
                "batch_size": 1,
                "warmup_iterations": 10,
                "main_iterations": 100,
                "confidence_threshold": 0.25,
                "test_images": "./data/test_images",
            },
            "output": {"directory": "./results", "formats": ["json"], "timestamp": True},
            "system_info": {"collect_gpu": False, "collect_power": True, "collect_temperature": True},
        }

        config = Config.from_dict(data=data, source_path=Path("./test_config.yaml"))

        self.assertEqual(config.benchmark.model_names, ["yolov8n", "yolov8s"])
        self.assertFalse(config.system_info.collect_gpu)


class TestReadYaml(unittest.TestCase):
    """Unit tests for the YAML loading helper."""

    def test_read_yaml_success(self) -> None:
        """
        Test successful loading and validation of a YAML configuration file.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - The YAML file is parsed successfully.
        - The resulting configuration contains the expected benchmark, output, and system info values.
        """
        yaml_content = """
        benchmark:
          runs:
            - models:
                - family: yolov8
                  sizes: [n, s, m]
            - models:
                - family: yolov11
                  sizes: [n, s]
          formats:
            - pytorch
            - onnx
            - tensorrt
            - openvino
          input_size: 640
          batch_size: 1
          warmup_iterations: 10
          main_iterations: 100
          confidence_threshold: 0.25
          test_images: \"./data/test_images\"
        output:
          directory: \"./results\"
          formats:
            - json
            - csv
            - markdown
          timestamp: true
        system_info:
          collect_gpu: true
          collect_power: true
          collect_temperature: true
        """

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as handle:
            handle.write(yaml_content)
            temp_path = Path(handle.name)

        try:
            config = read_yaml(temp_path)

            self.assertEqual(config.benchmark.model_names, ["yolov8n", "yolov8s", "yolov8m", "yolov11n", "yolov11s"])
            self.assertTrue(config.output.use_timestamp)
            self.assertTrue(config.system_info.collect_gpu)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_read_yaml_wrong_path_type(self) -> None:
        """
        Test read_yaml with a path that is not a Path instance.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - A TypeError is raised when a non-Path object is passed.
        """
        with self.assertRaises(TypeError):
            read_yaml("not-a-path")

    def test_read_yaml_missing_file(self) -> None:
        """
        Test read_yaml with a missing file path.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - A FileNotFoundError is raised for a missing YAML file.
        """
        missing_path = Path(__file__).with_name("missing.yaml")

        with self.assertRaises(FileNotFoundError):
            read_yaml(missing_path)

    def test_read_yaml_invalid_yaml(self) -> None:
        """
        Test read_yaml with malformed YAML content.

        Parameters:
        -----------
        None.

        Asserts:
        --------
        - A ConfigError is raised when the YAML content cannot be parsed.
        """
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as handle:
            handle.write("benchmark: [")
            temp_path = Path(handle.name)

        try:
            with self.assertRaises(ConfigError):
                read_yaml(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
