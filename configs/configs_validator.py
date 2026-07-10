from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class ConfigError(ValueError):
    """Configuration validation error."""


class _ModelInputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str
    size: str | None = None
    sizes: list[str] | None = None

    @field_validator("family")
    @classmethod
    def validate_family(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("family must be a non-empty string")
        return value.strip()

    @field_validator("size")
    @classmethod
    def validate_size(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value or not value.strip():
            raise ValueError("size must be a non-empty string")
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
        if self.size is not None and self.sizes is not None:
            raise ValueError("entry must contain either size or sizes, not both")
        if self.size is None and self.sizes is None:
            raise ValueError("entry must contain size or sizes")
        if self.size is not None:
            self.sizes = [self.size]
            self.size = None
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
    input_size: int | None = None
    batch_size: int | None = None
    warmup_iterations: int | None = None
    main_iterations: int | None = None
    confidence_threshold: float | None = None
    test_images: str | None = None

    @field_validator("formats")
    @classmethod
    def validate_formats(cls, value: list[str]) -> list[str]:
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError("formats must contain non-empty strings")
        return [item.strip() for item in value]

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