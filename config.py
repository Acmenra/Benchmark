"""Configuration loading and validation utilities for Edge AI Benchmark Suite.

This module contains strongly validated configuration classes and YAML parsing
helpers. It is intentionally independent from benchmark execution logic, so the
configuration layer can be reused from CLI, tests, notebooks, and external
Python code after package installation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

import yaml


class ConfigError(ValueError):
    """Base exception for configuration validation errors."""


class ModelConfig:
    """Configuration of a single model variant.

    Parameters:
    -----------
    family : str
        YOLO model family name, for example `yolov8` or `yolov11`.
    size : str
        Model size name, for example `n`, `s`, `m`, `l`, or `x`.
    """

    SUPPORTED_FAMILIES: ClassVar[set[str]] = {"yolov8", "yolov10", "yolov11", "yolov12", "yolov26"}
    SUPPORTED_SIZES: ClassVar[set[str]] = {"n", "s", "m", "l", "x"}

    def __init__(self, family: str, size: str) -> None:
        """Constructor for the ModelConfig object.

        Parameters:
        -----------
        family : str
            YOLO model family name.
        size : str
            Model size name.
        """
        self.family = family
        self.size = size

    @property
    def family(self) -> str:
        """Getter for the model family.

        Returns:
        --------
        str
            The configured model family name.
        """
        return self._family

    @family.setter
    def family(self, value: str) -> None:
        """Setter for the model family.

        Parameters:
        -----------
        value : str
            YOLO model family name.

        Raises:
        -------
        TypeError
            If the provided value is not a string.
        ConfigError
            If the provided value is empty or unsupported.
        """
        if not isinstance(value, str):
            raise TypeError("The provided 'family' value must be a string.")
        normalized_value = value.strip().lower()
        if not normalized_value:
            raise ConfigError("The provided 'family' value cannot be empty.")
        if normalized_value not in self.SUPPORTED_FAMILIES:
            raise ConfigError(
                "The provided 'family' value must be one of: "
                f"{sorted(self.SUPPORTED_FAMILIES)}."
            )
        self._family = normalized_value

    @property
    def size(self) -> str:
        """Getter for the model size.

        Returns:
        --------
        str
            The configured model size name.
        """
        return self._size

    @size.setter
    def size(self, value: str) -> None:
        """Setter for the model size.

        Parameters:
        -----------
        value : str
            Model size name.

        Raises:
        -------
        TypeError
            If the provided value is not a string.
        ConfigError
            If the provided value is empty or unsupported.
        """
        if not isinstance(value, str):
            raise TypeError("The provided 'size' value must be a string.")
        normalized_value = value.strip().lower()
        if not normalized_value:
            raise ConfigError("The provided 'size' value cannot be empty.")
        if normalized_value not in self.SUPPORTED_SIZES:
            raise ConfigError(
                "The provided 'size' value must be one of: "
                f"{sorted(self.SUPPORTED_SIZES)}."
            )
        self._size = normalized_value

    @property
    def name(self) -> str:
        """Getter for the full model name.

        Returns:
        --------
        str
            The full model name assembled from family and size, for example `yolov8n`.
        """
        return f"{self.family}{self.size}"

    def to_dict(self) -> Dict[str, str]:
        """Serialize the model configuration to a dictionary.

        Returns:
        --------
        Dict[str, str]
            A dictionary representation of the model configuration.
        """
        return {"family": self.family, "size": self.size, "name": self.name}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ModelConfig:
        """Create a model configuration from a dictionary.

        Parameters:
        -----------
        data : Dict[str, Any]
            Raw dictionary loaded from YAML.

        Returns:
        --------
        ModelConfig
            A validated model configuration.

        Raises:
        -------
        TypeError
            If the provided value is not a dictionary.
        ConfigError
            If required fields are missing or invalid.
        """
        if not isinstance(data, dict):
            raise TypeError("The provided model configuration must be a dictionary.")
        if "family" not in data:
            raise ConfigError("Model configuration must contain the 'family' field.")
        if "size" not in data:
            raise ConfigError("Model configuration must contain the 'size' field.")
        return ModelConfig(family=data["family"], size=data["size"])


class BenchmarkRun:
    """Configuration of one benchmark run.

    Parameters:
    -----------
    models : List[ModelConfig]
        A list of model variants that must be tested within one benchmark run.
    """

    def __init__(self, models: List[ModelConfig]) -> None:
        """Constructor for the BenchmarkRun object.

        Parameters:
        -----------
        models : List[ModelConfig]
            A list of validated model configurations.
        """
        self.models = models

    @property
    def models(self) -> List[ModelConfig]:
        """Getter for benchmark run models.

        Returns:
        --------
        List[ModelConfig]
            A copy of configured model variants.
        """
        return list(self._models)

    @models.setter
    def models(self, value: List[ModelConfig]) -> None:
        """Setter for benchmark run models.

        Parameters:
        -----------
        value : List[ModelConfig]
            A non-empty list of validated model configurations.

        Raises:
        -------
        TypeError
            If the provided value is not a list of ModelConfig instances.
        ConfigError
            If the provided list is empty or contains duplicates.
        """
        if not isinstance(value, list):
            raise TypeError("The provided 'models' value must be a list.")
        if not value:
            raise ConfigError("The provided 'models' list cannot be empty.")
        if not all(isinstance(model, ModelConfig) for model in value):
            raise TypeError("Each item in 'models' must be an instance of ModelConfig.")
        model_names = [model.name for model in value]
        if len(model_names) != len(set(model_names)):
            raise ConfigError("The provided 'models' list cannot contain duplicate model variants.")
        self._models = tuple(value)

    @property
    def model_names(self) -> List[str]:
        """Getter for benchmark run model names.

        Returns:
        --------
        List[str]
            A list of full model names included in the benchmark run.
        """
        return [model.name for model in self._models]

    def to_dict(self) -> Dict[str, List[Dict[str, str]]]:
        """Serialize the benchmark run to a dictionary.

        Returns:
        --------
        Dict[str, List[Dict[str, str]]]
            A dictionary representation of the benchmark run.
        """
        return {"models": [model.to_dict() for model in self._models]}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> BenchmarkRun:
        """Create a benchmark run from a dictionary.

        The YAML input supports two forms:
        - one model with multiple sizes, for example `sizes: [n, s, m]`;
        - several models where each model must contain exactly one size.

        Parameters:
        -----------
        data : Dict[str, Any]
            Raw dictionary loaded from YAML.

        Returns:
        --------
        BenchmarkRun
            A validated benchmark run configuration.

        Raises:
        -------
        TypeError
            If the provided value is not a dictionary.
        ConfigError
            If required fields are missing or invalid.
        """
        if not isinstance(data, dict):
            raise TypeError("The provided benchmark run configuration must be a dictionary.")
        if "models" not in data:
            raise ConfigError("Benchmark run configuration must contain the 'models' field.")
        raw_models = data["models"]
        if not isinstance(raw_models, list):
            raise TypeError("The provided 'models' field must be a list.")
        if not raw_models:
            raise ConfigError("The provided 'models' field cannot be empty.")

        expanded_models = BenchmarkRun._parse_models(raw_models=raw_models)
        return BenchmarkRun(models=expanded_models)

    @staticmethod
    def _parse_models(raw_models: List[Any]) -> List[ModelConfig]:
        """Parse and normalize raw model definitions.

        Parameters:
        -----------
        raw_models : List[Any]
            Raw model definitions loaded from YAML.

        Returns:
        --------
        List[ModelConfig]
            A normalized list of model configurations.

        Raises:
        -------
        TypeError
            If a model item has an invalid type.
        ConfigError
            If model sizes are missing or violate run composition rules.
        """
        if len(raw_models) == 1:
            return BenchmarkRun._parse_single_model_run(raw_model=raw_models[0])
        return BenchmarkRun._parse_multi_model_run(raw_models=raw_models)

    @staticmethod
    def _parse_single_model_run(raw_model: Any) -> List[ModelConfig]:
        """Parse a benchmark run with one model family and one or more sizes.

        Parameters:
        -----------
        raw_model : Any
            Raw model definition loaded from YAML.

        Returns:
        --------
        List[ModelConfig]
            A list of expanded model configurations.
        """
        if not isinstance(raw_model, dict):
            raise TypeError("Each model definition must be a dictionary.")
        if "family" not in raw_model:
            raise ConfigError("Each model definition must contain the 'family' field.")
        sizes = BenchmarkRun._extract_sizes(raw_model=raw_model)
        return [ModelConfig(family=raw_model["family"], size=size) for size in sizes]

    @staticmethod
    def _parse_multi_model_run(raw_models: List[Any]) -> List[ModelConfig]:
        """Parse a benchmark run with several model families.

        Parameters:
        -----------
        raw_models : List[Any]
            Raw model definitions loaded from YAML.

        Returns:
        --------
        List[ModelConfig]
            A list of model configurations.

        Raises:
        -------
        TypeError
            If a model definition has an invalid type.
        ConfigError
            If any model definition contains more than one size.
        """
        models: List[ModelConfig] = []
        for raw_model in raw_models:
            if not isinstance(raw_model, dict):
                raise TypeError("Each model definition must be a dictionary.")
            if "family" not in raw_model:
                raise ConfigError("Each model definition must contain the 'family' field.")
            sizes = BenchmarkRun._extract_sizes(raw_model=raw_model)
            if len(sizes) != 1:
                raise ConfigError(
                    "When a benchmark run contains several models, each model must contain exactly one size."
                )
            models.append(ModelConfig(family=raw_model["family"], size=sizes[0]))
        return models

    @staticmethod
    def _extract_sizes(raw_model: Dict[str, Any]) -> List[str]:
        """Extract model sizes from a raw model definition.

        Parameters:
        -----------
        raw_model : Dict[str, Any]
            Raw model definition loaded from YAML.

        Returns:
        --------
        List[str]
            A non-empty list of model sizes.

        Raises:
        -------
        ConfigError
            If neither `size` nor `sizes` is provided, or if both are provided.
        TypeError
            If size values have invalid types.
        """
        has_size = "size" in raw_model
        has_sizes = "sizes" in raw_model
        if has_size and has_sizes:
            raise ConfigError("Use either 'size' or 'sizes' for a model definition, not both.")
        if not has_size and not has_sizes:
            raise ConfigError("Each model definition must contain either 'size' or 'sizes'.")
        if has_size:
            size = raw_model["size"]
            if not isinstance(size, str):
                raise TypeError("The provided 'size' value must be a string.")
            return [size]

        sizes = raw_model["sizes"]
        if not isinstance(sizes, list):
            raise TypeError("The provided 'sizes' value must be a list.")
        if not sizes:
            raise ConfigError("The provided 'sizes' value cannot be empty.")
        if not all(isinstance(size, str) for size in sizes):
            raise TypeError("Each item in 'sizes' must be a string.")
        return sizes


class BenchmarkConfig:
    """Configuration of benchmark execution parameters.

    Parameters:
    -----------
    runs : List[BenchmarkRun]
        A list of benchmark runs.
    formats : List[str]
        Model formats to benchmark.
    input_size : int
        Input image size used for inference.
    batch_size : int
        Batch size used for inference.
    warmup_iterations : int
        Number of warmup iterations excluded from final metrics.
    main_iterations : int
        Number of measured benchmark iterations.
    confidence_threshold : float
        Detection confidence threshold.
    test_images : Path
        Path to a directory with local test images.
    """

    SUPPORTED_FORMATS: ClassVar[set[str]] = {"pytorch", "onnx", "tensorrt", "openvino"}

    def __init__(
        self,
        runs: List[BenchmarkRun],
        formats: List[str],
        input_size: int,
        batch_size: int,
        warmup_iterations: int,
        main_iterations: int,
        confidence_threshold: float,
        test_images: Path,
    ) -> None:
        """Constructor for the BenchmarkConfig object.

        Parameters:
        -----------
        runs : List[BenchmarkRun]
            A list of validated benchmark runs.
        formats : List[str]
            Model formats to benchmark.
        input_size : int
            Input image size used for inference.
        batch_size : int
            Batch size used for inference.
        warmup_iterations : int
            Number of warmup iterations.
        main_iterations : int
            Number of measured iterations.
        confidence_threshold : float
            Detection confidence threshold.
        test_images : Path
            Path to local test images.
        """
        self.runs = runs
        self.formats = formats
        self.input_size = input_size
        self.batch_size = batch_size
        self.warmup_iterations = warmup_iterations
        self.main_iterations = main_iterations
        self.confidence_threshold = confidence_threshold
        self.test_images = test_images

    @property
    def runs(self) -> List[BenchmarkRun]:
        """Getter for benchmark runs.

        Returns:
        --------
        List[BenchmarkRun]
            A copy of configured benchmark runs.
        """
        return list(self._runs)

    @runs.setter
    def runs(self, value: List[BenchmarkRun]) -> None:
        """Setter for benchmark runs.

        Parameters:
        -----------
        value : List[BenchmarkRun]
            A non-empty list of benchmark runs.
        
        Raises:
        -------
        TypeError
            If the provided value is not a list of BenchmarkRun instances.
        ConfigError
            If the provided list is empty.
        """
        if not isinstance(value, list):
            raise TypeError("The provided 'runs' value must be a list.")
        if not value:
            raise ConfigError("The provided 'runs' value cannot be empty.")
        if not all(isinstance(run, BenchmarkRun) for run in value):
            raise TypeError("Each item in 'runs' must be an instance of BenchmarkRun.")
        self._runs = tuple(value)

    @property
    def formats(self) -> List[str]:
        """Getter for benchmark formats.

        Returns:
        --------
        List[str]
            A copy of configured model formats.
        """
        return list(self._formats)

    @formats.setter
    def formats(self, value: List[str]) -> None:
        """Setter for benchmark formats.

        Parameters:
        -----------
        value : List[str]
            Model formats to benchmark.

        Raises:
        -------
        TypeError
            If the provided value is not a list of strings.
        ConfigError
            If the provided list is empty, contains unsupported formats, or has duplicates.
        """
        if not isinstance(value, list):
            raise TypeError("The provided 'formats' value must be a list.")
        if not value:
            raise ConfigError("The provided 'formats' value cannot be empty.")
        if not all(isinstance(item, str) for item in value):
            raise TypeError("Each item in 'formats' must be a string.")
        normalized_formats = [item.strip().lower() for item in value]
        if any(not item for item in normalized_formats):
            raise ConfigError("The provided 'formats' value cannot contain empty strings.")
        unsupported_formats = sorted(set(normalized_formats) - self.SUPPORTED_FORMATS)
        if unsupported_formats:
            raise ConfigError(f"Unsupported benchmark formats: {unsupported_formats}.")
        if len(normalized_formats) != len(set(normalized_formats)):
            raise ConfigError("The provided 'formats' value cannot contain duplicates.")
        self._formats = tuple(normalized_formats)

    @property
    def input_size(self) -> int:
        """Getter for input image size.

        Returns:
        --------
        int
            The configured input image size.
        """
        return self._input_size

    @input_size.setter
    def input_size(self, value: int) -> None:
        """Setter for input image size.

        Parameters:
        -----------
        value : int
            Positive input image size.
        
        Raises:
        -------
        TypeError
            If the provided value is not an integer.
        ConfigError
            If the provided value is not greater than zero.
        """
        self._input_size = self._validate_positive_int(value=value, field_name="input_size")

    @property
    def batch_size(self) -> int:
        """Getter for batch size.

        Returns:
        --------
        int
            The configured batch size.
        """
        return self._batch_size

    @batch_size.setter
    def batch_size(self, value: int) -> None:
        """Setter for batch size.

        Parameters:
        -----------
        value : int
            Positive batch size.
        
        Raises:
        -------
        TypeError
            If the provided value is not an integer.
        ConfigError
            If the provided value is not greater than zero.
        """
        self._batch_size = self._validate_positive_int(value=value, field_name="batch_size")

    @property
    def warmup_iterations(self) -> int:
        """Getter for warmup iterations.

        Returns:
        --------
        int
            The configured number of warmup iterations.
        """
        return self._warmup_iterations

    @warmup_iterations.setter
    def warmup_iterations(self, value: int) -> None:
        """Setter for warmup iterations.

        Parameters:
        -----------
        value : int
            Non-negative number of warmup iterations.
        
        Raises:
        -------
        TypeError
            If the provided value is not an integer.
        ConfigError
            If the provided value is negative.
        """
        self._warmup_iterations = self._validate_non_negative_int(
            value=value,
            field_name="warmup_iterations",
        )

    @property
    def main_iterations(self) -> int:
        """Getter for main benchmark iterations.

        Returns:
        --------
        int
            The configured number of measured benchmark iterations.
        """
        return self._main_iterations

    @main_iterations.setter
    def main_iterations(self, value: int) -> None:
        """Setter for main benchmark iterations.

        Parameters:
        -----------
        value : int
            Positive number of measured benchmark iterations.
        
        Raises:
        -------
        TypeError
            If the provided value is not an integer.
        ConfigError
            If the provided value is not greater than zero.
        """
        self._main_iterations = self._validate_positive_int(value=value, field_name="main_iterations")

    @property
    def confidence_threshold(self) -> float:
        """Getter for confidence threshold.

        Returns:
        --------
        float
            The configured confidence threshold.
        """
        return self._confidence_threshold

    @confidence_threshold.setter
    def confidence_threshold(self, value: float) -> None:
        """Setter for confidence threshold.

        Parameters:
        -----------
        value : float
            Confidence threshold in the [0.0, 1.0] range.
        
        Raises:
        -------
        TypeError
            If the provided value is not a float/int or boolean.
        ConfigError
            If the provided value is not in the [0.0, 1.0] range.
        """
        if not isinstance(value, (float, int)) or isinstance(value, bool):
            raise TypeError("The provided 'confidence_threshold' value must be a float.")
        normalized_value = float(value)
        if not 0.0 <= normalized_value <= 1.0:
            raise ConfigError("The provided 'confidence_threshold' value must be in the [0.0, 1.0] range.")
        self._confidence_threshold = normalized_value

    @property
    def test_images(self) -> Path:
        """Getter for test images path.

        Returns:
        --------
        Path
            The configured path to local test images.
        """
        return self._test_images

    @test_images.setter
    def test_images(self, value: Path) -> None:
        """Setter for test images path.

        Parameters:
        -----------
        value : Path
            Path to a local test images directory.
        
        Raises:
        -------
        TypeError
            If the provided value is not an instance of Path.
        """
        if not isinstance(value, Path):
            raise TypeError("The provided 'test_images' value must be an instance of Path.")
        self._test_images = value

    @property
    def model_names(self) -> List[str]:
        """Getter for all model names across benchmark runs.

        Returns:
        --------
        List[str]
            A list of full model names configured for all benchmark runs.
        """
        return [model_name for run in self._runs for model_name in run.model_names]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the benchmark configuration to a dictionary.

        Returns:
        --------
        Dict[str, Any]
            A dictionary representation of the benchmark configuration.
        """
        return {
            "runs": [run.to_dict() for run in self._runs],
            "formats": list(self._formats),
            "input_size": self.input_size,
            "batch_size": self.batch_size,
            "warmup_iterations": self.warmup_iterations,
            "main_iterations": self.main_iterations,
            "confidence_threshold": self.confidence_threshold,
            "test_images": str(self.test_images),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> BenchmarkConfig:
        """Create benchmark configuration from a dictionary.

        Parameters:
        -----------
        data : Dict[str, Any]
            Raw benchmark configuration loaded from YAML.

        Returns:
        --------
        BenchmarkConfig
            A validated benchmark configuration.
        """
        if not isinstance(data, dict):
            raise TypeError("The provided benchmark configuration must be a dictionary.")
        required_fields = {
            "runs",
            "formats",
            "input_size",
            "batch_size",
            "warmup_iterations",
            "main_iterations",
            "confidence_threshold",
            "test_images",
        }
        BenchmarkConfig._check_required_fields(data=data, required_fields=required_fields, section_name="benchmark")
        raw_runs = data["runs"]
        if not isinstance(raw_runs, list):
            raise TypeError("The provided 'benchmark.runs' value must be a list.")
        runs = [BenchmarkRun.from_dict(run) for run in raw_runs]
        return BenchmarkConfig(
            runs=runs,
            formats=data["formats"],
            input_size=data["input_size"],
            batch_size=data["batch_size"],
            warmup_iterations=data["warmup_iterations"],
            main_iterations=data["main_iterations"],
            confidence_threshold=data["confidence_threshold"],
            test_images=Path(data["test_images"]),
        )

    @staticmethod
    def _check_required_fields(data: Dict[str, Any], required_fields: set[str], section_name: str) -> None:
        """Validate that required fields exist in a configuration section.

        Parameters:
        -----------
        data : Dict[str, Any]
            Configuration section dictionary.
        required_fields : set[str]
            Required field names.
        section_name : str
            Human-readable section name used in error messages.
        """
        missing_fields = sorted(required_fields - data.keys())
        if missing_fields:
            raise ConfigError(f"Missing required fields in '{section_name}': {missing_fields}.")

    @staticmethod
    def _validate_positive_int(value: int, field_name: str) -> int:
        """Validate a positive integer value.

        Parameters:
        -----------
        value : int
            Value to validate.
        field_name : str
            Field name used in error messages.

        Returns:
        --------
        int
            The validated integer value.
        """
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"The provided '{field_name}' value must be an integer.")
        if value <= 0:
            raise ConfigError(f"The provided '{field_name}' value must be greater than zero.")
        return value

    @staticmethod
    def _validate_non_negative_int(value: int, field_name: str) -> int:
        """Validate a non-negative integer value.

        Parameters:
        -----------
        value : int
            Value to validate.
        field_name : str
            Field name used in error messages.

        Returns:
        --------
        int
            The validated integer value.
        """
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"The provided '{field_name}' value must be an integer.")
        if value < 0:
            raise ConfigError(f"The provided '{field_name}' value must be greater than or equal to zero.")
        return value


class SystemInfoConfig:
    """Configuration of system information collection.

    Parameters:
    -----------
    collect_gpu : bool
        Whether GPU information should be collected.
    collect_power : bool
        Whether power information should be collected.
    collect_temperature : bool
        Whether temperature information should be collected.
    """

    def __init__(self, collect_gpu: bool, collect_power: bool, collect_temperature: bool) -> None:
        """Constructor for the SystemInfoConfig object.

        Parameters:
        -----------
        collect_gpu : bool
            Whether GPU information should be collected.
        collect_power : bool
            Whether power information should be collected.
        collect_temperature : bool
            Whether temperature information should be collected.
        """
        self.collect_gpu = collect_gpu
        self.collect_power = collect_power
        self.collect_temperature = collect_temperature

    @property
    def collect_gpu(self) -> bool:
        """Getter for the GPU collection flag.

        Returns:
        --------
        bool
            The configured GPU collection flag.
        """
        return self._collect_gpu

    @collect_gpu.setter
    def collect_gpu(self, value: bool) -> None:
        """Setter for the GPU collection flag.

        Parameters:
        -----------
        value : bool
            Whether GPU information should be collected.
        """
        self._collect_gpu = self._validate_bool(value=value, field_name="collect_gpu")

    @property
    def collect_power(self) -> bool:
        """Getter for the power collection flag.

        Returns:
        --------
        bool
            The configured power collection flag.
        """
        return self._collect_power

    @collect_power.setter
    def collect_power(self, value: bool) -> None:
        """Setter for the power collection flag.

        Parameters:
        -----------
        value : bool
            Whether power information should be collected.
        """
        self._collect_power = self._validate_bool(value=value, field_name="collect_power")

    @property
    def collect_temperature(self) -> bool:
        """Getter for the temperature collection flag.

        Returns:
        --------
        bool
            The configured temperature collection flag.
        """
        return self._collect_temperature

    @collect_temperature.setter
    def collect_temperature(self, value: bool) -> None:
        """Setter for the temperature collection flag.

        Parameters:
        -----------
        value : bool
            Whether temperature information should be collected.
        """
        self._collect_temperature = self._validate_bool(value=value, field_name="collect_temperature")

    def to_dict(self) -> Dict[str, bool]:
        """Serialize the system information configuration to a dictionary.

        Returns:
        --------
        Dict[str, bool]
            A dictionary representation of the system information configuration.
        """
        return {
            "collect_gpu": self.collect_gpu,
            "collect_power": self.collect_power,
            "collect_temperature": self.collect_temperature,
        }

    @staticmethod
    def from_dict(data: Optional[Dict[str, Any]]) -> SystemInfoConfig:
        """Create system information configuration from a dictionary.

        Parameters:
        -----------
        data : Optional[Dict[str, Any]]
            Raw system information configuration loaded from YAML.

        Returns:
        --------
        SystemInfoConfig
            A validated system information configuration.
        """
        if data is None:
            return SystemInfoConfig(collect_gpu=True, collect_power=True, collect_temperature=True)
        if not isinstance(data, dict):
            raise TypeError("The provided system information configuration must be a dictionary.")
        return SystemInfoConfig(
            collect_gpu=data.get("collect_gpu", True),
            collect_power=data.get("collect_power", True),
            collect_temperature=data.get("collect_temperature", True),
        )

    @staticmethod
    def _validate_bool(value: bool, field_name: str) -> bool:
        """Validate a boolean configuration value.

        Parameters:
        -----------
        value : bool
            Value to validate.
        field_name : str
            Field name used in error messages.

        Returns:
        --------
        bool
            The validated boolean value.
        """
        if not isinstance(value, bool):
            raise TypeError(f"The provided '{field_name}' value must be a boolean.")
        return value


class OutputConfig:
    """Configuration of benchmark output generation.

    Parameters:
    -----------
    directory : Path
        Directory where benchmark reports must be written.
    formats : List[str]
        Report formats to generate.
    use_timestamp : bool
        Whether timestamped output directories or files should be used.
    """

    SUPPORTED_FORMATS: ClassVar[set[str]] = {"json", "csv", "markdown", "md"}

    def __init__(self, directory: Path, formats: List[str], use_timestamp: bool) -> None:
        """Constructor for the OutputConfig object.

        Parameters:
        -----------
        directory : Path
            Directory where benchmark reports must be written.
        formats : List[str]
            Report formats to generate.
        use_timestamp : bool
            Whether timestamped output paths should be used.
        """
        self.directory = directory
        self.formats = formats
        self.use_timestamp = use_timestamp

    @property
    def directory(self) -> Path:
        """Getter for the output directory.

        Returns:
        --------
        Path
            The configured output directory.
        """
        return self._directory

    @directory.setter
    def directory(self, value: Path) -> None:
        """Setter for the output directory.

        Parameters:
        -----------
        value : Path
            Directory where benchmark reports must be written.
        """
        if not isinstance(value, Path):
            raise TypeError("The provided 'directory' value must be an instance of Path.")
        self._directory = value

    @property
    def formats(self) -> List[str]:
        """Getter for output formats.

        Returns:
        --------
        List[str]
            A copy of configured output formats.
        """
        return list(self._formats)

    @formats.setter
    def formats(self, value: List[str]) -> None:
        """Setter for output formats.

        Parameters:
        -----------
        value : List[str]
            Report formats to generate.
        """
        if not isinstance(value, list):
            raise TypeError("The provided 'formats' value must be a list.")
        if not value:
            raise ConfigError("The provided output 'formats' value cannot be empty.")
        if not all(isinstance(item, str) for item in value):
            raise TypeError("Each item in output 'formats' must be a string.")
        normalized_formats = ["markdown" if item.strip().lower() == "md" else item.strip().lower() for item in value]
        if any(not item for item in normalized_formats):
            raise ConfigError("The provided output 'formats' value cannot contain empty strings.")
        unsupported_formats = sorted(set(normalized_formats) - {"json", "csv", "markdown"})
        if unsupported_formats:
            raise ConfigError(f"Unsupported output formats: {unsupported_formats}.")
        if len(normalized_formats) != len(set(normalized_formats)):
            raise ConfigError("The provided output 'formats' value cannot contain duplicates.")
        self._formats = tuple(normalized_formats)

    @property
    def use_timestamp(self) -> bool:
        """Getter for the timestamp flag.

        Returns:
        --------
        bool
            The configured timestamp flag.
        """
        return self._use_timestamp

    @use_timestamp.setter
    def use_timestamp(self, value: bool) -> None:
        """Setter for the timestamp flag.

        Parameters:
        -----------
        value : bool
            Whether timestamped output paths should be used.
        """
        if not isinstance(value, bool):
            raise TypeError("The provided 'use_timestamp' value must be a boolean.")
        self._use_timestamp = value

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the output configuration to a dictionary.

        Returns:
        --------
        Dict[str, Any]
            A dictionary representation of the output configuration.
        """
        return {
            "directory": str(self.directory),
            "formats": list(self._formats),
            "timestamp": self.use_timestamp,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> OutputConfig:
        """Create output configuration from a dictionary.

        Parameters:
        -----------
        data : Dict[str, Any]
            Raw output configuration loaded from YAML.

        Returns:
        --------
        OutputConfig
            A validated output configuration.
        """
        if not isinstance(data, dict):
            raise TypeError("The provided output configuration must be a dictionary.")
        required_fields = {"directory", "formats", "timestamp"}
        missing_fields = sorted(required_fields - data.keys())
        if missing_fields:
            raise ConfigError(f"Missing required fields in 'output': {missing_fields}.")
        if not isinstance(data["directory"], str):
            raise TypeError("The provided 'output.directory' value must be a string.")
        return OutputConfig(
            directory=Path(data["directory"]),
            formats=data["formats"],
            use_timestamp=data["timestamp"],
        )


class Config:
    """Root application configuration.

    Parameters:
    -----------
    benchmark : BenchmarkConfig
        Benchmark execution configuration.
    system_info : SystemInfoConfig
        System information collection configuration.
    output : OutputConfig
        Benchmark output configuration.
    source_path : Optional[Path]
        Optional path to the YAML file used to create this configuration.
    """

    def __init__(
        self,
        benchmark: BenchmarkConfig,
        system_info: SystemInfoConfig,
        output: OutputConfig,
        source_path: Optional[Path] = None,
    ) -> None:
        """Constructor for the Config object.

        Parameters:
        -----------
        benchmark : BenchmarkConfig
            Benchmark execution configuration.
        system_info : SystemInfoConfig
            System information collection configuration.
        output : OutputConfig
            Benchmark output configuration.
        source_path : Optional[Path]
            Optional path to the YAML source file.
        """
        self.benchmark = benchmark
        self.system_info = system_info
        self.output = output
        self.source_path = source_path

    @property
    def benchmark(self) -> BenchmarkConfig:
        """Getter for benchmark configuration.

        Returns:
        --------
        BenchmarkConfig
            The configured benchmark section.
        """
        return self._benchmark

    @benchmark.setter
    def benchmark(self, value: BenchmarkConfig) -> None:
        """Setter for benchmark configuration.

        Parameters:
        -----------
        value : BenchmarkConfig
            Benchmark execution configuration.
        """
        if not isinstance(value, BenchmarkConfig):
            raise TypeError("The provided 'benchmark' value must be an instance of BenchmarkConfig.")
        self._benchmark = value

    @property
    def system_info(self) -> SystemInfoConfig:
        """Getter for system information configuration.

        Returns:
        --------
        SystemInfoConfig
            The configured system information section.
        """
        return self._system_info

    @system_info.setter
    def system_info(self, value: SystemInfoConfig) -> None:
        """Setter for system information configuration.

        Parameters:
        -----------
        value : SystemInfoConfig
            System information collection configuration.
        """
        if not isinstance(value, SystemInfoConfig):
            raise TypeError("The provided 'system_info' value must be an instance of SystemInfoConfig.")
        self._system_info = value

    @property
    def output(self) -> OutputConfig:
        """Getter for output configuration.

        Returns:
        --------
        OutputConfig
            The configured output section.
        """
        return self._output

    @output.setter
    def output(self, value: OutputConfig) -> None:
        """Setter for output configuration.

        Parameters:
        -----------
        value : OutputConfig
            Benchmark output configuration.
        """
        if not isinstance(value, OutputConfig):
            raise TypeError("The provided 'output' value must be an instance of OutputConfig.")
        self._output = value

    @property
    def source_path(self) -> Optional[Path]:
        """Getter for source YAML path.

        Returns:
        --------
        Optional[Path]
            The YAML source path or None if the configuration was created manually.
        """
        return self._source_path

    @source_path.setter
    def source_path(self, value: Optional[Path]) -> None:
        """Setter for source YAML path.

        Parameters:
        -----------
        value : Optional[Path]
            Optional YAML source path.
        """
        if value is not None and not isinstance(value, Path):
            raise TypeError("The provided 'source_path' value must be an instance of Path or None.")
        self._source_path = value

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the root configuration to a dictionary.

        Returns:
        --------
        Dict[str, Any]
            A dictionary representation of the root configuration.
        """
        return {
            "benchmark": self.benchmark.to_dict(),
            "system_info": self.system_info.to_dict(),
            "output": self.output.to_dict(),
            "source_path": str(self.source_path) if self.source_path is not None else None,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any], source_path: Optional[Path] = None) -> Config:
        """Create root configuration from a dictionary.

        Parameters:
        -----------
        data : Dict[str, Any]
            Raw root configuration loaded from YAML.
        source_path : Optional[Path]
            Optional YAML source path.

        Returns:
        --------
        Config
            A validated root configuration.
        """
        if not isinstance(data, dict):
            raise TypeError("The provided root configuration must be a dictionary.")
        required_fields = {"benchmark", "output"}
        missing_fields = sorted(required_fields - data.keys())
        if missing_fields:
            raise ConfigError(f"Missing required root configuration sections: {missing_fields}.")
        return Config(
            benchmark=BenchmarkConfig.from_dict(data=data["benchmark"]),
            system_info=SystemInfoConfig.from_dict(data=data.get("system_info")),
            output=OutputConfig.from_dict(data=data["output"]),
            source_path=source_path,
        )


def read_yaml(path: Path) -> Config:
    """Read, parse, and validate a YAML configuration file.

    Parameters:
    -----------
    path : Path
        Path to a YAML configuration file.

    Returns:
    --------
    Config
        A validated root configuration object.

    Raises:
    -------
    TypeError
        If the provided path is not an instance of Path.
    FileNotFoundError
        If the configuration file does not exist.
    ConfigError
        If YAML content is empty, invalid, or does not match the expected schema.
    """
    if not isinstance(path, Path):
        raise TypeError("The provided 'path' value must be an instance of Path.")
    if not path.exists():
        raise FileNotFoundError(f"The configuration file was not found: {path}.")
    if not path.is_file():
        raise ConfigError(f"The configuration path must point to a file: {path}.")

    try:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except yaml.YAMLError as error:
        raise ConfigError(f"Failed to parse YAML configuration file: {path}.") from error

    if data is None:
        raise ConfigError(f"The configuration file is empty: {path}.")
    if not isinstance(data, dict):
        raise ConfigError("The root YAML configuration must be a dictionary.")
    return Config.from_dict(data=data, source_path=path)
