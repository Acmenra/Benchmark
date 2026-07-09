from __future__ import annotations

from typing import Any


class ConfigError(ValueError):
    pass


class ConfigsValidator:
    """Валидация полей конфигурации."""

    @staticmethod
    def validate_str_list(value: Any, *, field_name: str) -> tuple[str, ...]:
        if value is None:
            return ()
        if not isinstance(value, list):
            raise ConfigError(f"{field_name} must be a list")
        if not all(isinstance(item, str) and item for item in value):
            raise ConfigError(f"{field_name} must contain only non-empty strings")
        return tuple(value)

    @classmethod
    def parse_models(cls, raw_models: Any, *, field_name: str) -> tuple[dict[str, str], ...]:
        if not isinstance(raw_models, list):
            raise ConfigError(f"{field_name} must be a list")
        if not raw_models:
            raise ConfigError(f"{field_name} must not be empty")

        models: list[dict[str, str]] = []
        for item in raw_models:
            if not isinstance(item, dict):
                raise ConfigError(f"{field_name} entries must be mappings")

            family = item.get("family")
            if not isinstance(family, str) or not family:
                raise ConfigError(f"{field_name} entry must contain a non-empty family")

            size = item.get("size")
            sizes = item.get("sizes")
            if size is None and sizes is None:
                raise ConfigError(f"{field_name} entry must contain size or sizes")

            if sizes is not None:
                if not isinstance(sizes, list) or not sizes:
                    raise ConfigError(f"{field_name} entry sizes must be a non-empty list")
                if len(raw_models) > 1 and len(sizes) != 1:
                    raise ConfigError("multiple models in one run require a single size for each model")
                for entry_size in sizes:
                    if not isinstance(entry_size, str) or not entry_size:
                        raise ConfigError(f"{field_name} entry sizes must contain non-empty strings")
                    models.append({"family": family, "size": entry_size})
            else:
                if not isinstance(size, str) or not size:
                    raise ConfigError(f"{field_name} entry size must be a non-empty string")
                models.append({"family": family, "size": size})