# infrastructure/config/configs_validator.py

import logging
from typing import Any

from core.enums.model import DeviceType, QuantizationLevel, TaskType
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

logger = logging.getLogger(__name__)


class ConfigError(ValueError):
    """Configuration validation error."""


class _ModelInputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str
    sizes: list[str] | None = None

    @field_validator("family")
    @classmethod
    def validate_family(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("family must be a non-empty string")
        return value.strip()

    @field_validator("sizes")
    @classmethod
    def validate_sizes(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("sizes must be a non-empty list")
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError("sizes must contain non-empty strings")
        return [item.strip() for item in value]

    @model_validator(mode="after")
    def validate_size_presence(self) -> "_ModelInputSchema":
        if self.sizes is None:
            raise ValueError("entry must contain sizes")
        return self


class _BenchmarkRunInputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    models: list[_ModelInputSchema]

    @field_validator("models")
    @classmethod
    def validate_models(cls, value: list[_ModelInputSchema]) -> list[_ModelInputSchema]:
        if not value:
            raise ValueError("models must not be empty")
        return value

    @model_validator(mode="after")
    def validate_sizes_for_multiple_models(self) -> "_BenchmarkRunInputSchema":
        if len(self.models) > 1:
            for model in self.models:
                if model.sizes is not None and len(model.sizes) != 1:
                    raise ValueError("multiple models in one run require a single size for each model")
        return self


class _BenchmarkConfigInputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runs: list[_BenchmarkRunInputSchema] = Field(default_factory=list)
    formats: list[str] = Field(default_factory=list)
    quantization: list[str] = Field(default_factory=list)
    input_size: int | None = None
    batch_size: int | None = None
    warmup_iterations: int | None = None
    main_iterations: int | None = None
    confidence_threshold: float | None = None
    test_images: str | None = None
    task_type: str | None = None
    device_type: str | None = None

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: str | TaskType | None) -> str | None:
        if value is None:
            return None

        if isinstance(value, TaskType):
            return value.value.lower()

        if not isinstance(value, str):
            raise ValueError("task_type must be a non-empty string")

        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("task_type must be a non-empty string")

        try:
            TaskType(normalized)
        except ValueError as exc:
            valid_values = sorted(item.value for item in TaskType)
            raise ValueError(
                f"task_type must contain valid values {valid_values}, got {value}"
            ) from exc
        return normalized

    @field_validator("device_type")
    @classmethod
    def validate_device_type(cls, value: str | DeviceType | None) -> str | None:
        if value is None:
            return None

        if isinstance(value, DeviceType):
            return value.value.lower()

        if not isinstance(value, str):
            raise ValueError("device_type must be a non-empty string")

        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("device_type must be a non-empty string")

        try:
            DeviceType(normalized)
        except ValueError as exc:
            raise ValueError(f"device_type must be a valid device string, got {value}") from exc
        return normalized
    
    @field_validator("formats")
    @classmethod
    def validate_formats(cls, value: list[str]) -> list[str]:
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError("formats must contain non-empty strings")
        return [item.strip() for item in value]

    @field_validator("quantization", mode="before")
    @classmethod
    def normalize_quantization(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return value

    @field_validator("quantization")
    @classmethod
    def validate_quantization(cls, value: list[str]) -> list[str]:
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError("quantization must contain non-empty strings")

        normalized_values = [item.strip().lower() for item in value]
        valid_values = {item.value for item in QuantizationLevel}
        invalid_values = [
            item for item in normalized_values
            if item not in valid_values
        ]
        if invalid_values:
            raise ValueError(
                f"quantization must contain valid values {sorted(valid_values)}, "
                f"got {invalid_values}"
            )

        return normalized_values

    @field_validator("test_images")
    @classmethod
    def validate_test_images(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value or not value.strip():
            raise ValueError("test_images must be a non-empty string")
        return value.strip()


class _SystemInfoInputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    collect_cpu: bool = False
    collect_gpu: bool = False
    collect_power: bool = False
    collect_temperature: bool = False


class _OutputInputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    directory: str
    formats: list[str] = Field(default_factory=list)
    timestamp: bool = False
    use_timestamp: bool = False

    @field_validator("directory")
    @classmethod
    def validate_directory(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("output.directory must be a non-empty string")
        return value.strip()

    @field_validator("formats")
    @classmethod
    def validate_formats(cls, value: list[str]) -> list[str]:
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError("output.formats must contain non-empty strings")
        return [item.strip() for item in value]

    @model_validator(mode="after")
    def normalize_timestamp(self) -> "_OutputInputSchema":
        if self.timestamp or self.use_timestamp:
            self.use_timestamp = True
        return self


class _ConfigInputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark: _BenchmarkConfigInputSchema | None = None
    system_info: _SystemInfoInputSchema | None = None
    output: _OutputInputSchema


class ConfigsValidator:
    """Pydantic-based configuration validation."""

    @classmethod
    def validate(cls, raw_data: Any) -> _ConfigInputSchema:
        if raw_data is None:
            raw_data = {}
        if not isinstance(raw_data, dict):
            raise ConfigError("YAML root must be a mapping")

        try:
            return _ConfigInputSchema.model_validate(raw_data)
        except ValidationError as exc:
            raise ConfigError(cls._format_error(exc)) from exc

    @staticmethod
    def _format_error(exc: ValidationError) -> str:
        first_error = exc.errors()[0]
        location = ".".join(str(part) for part in first_error.get("loc", ()))
        message = first_error.get("msg", "validation failed")
        return f"{location or 'config'}: {message}" if location else message
