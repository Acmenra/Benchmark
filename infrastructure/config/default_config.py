# infrastructure/config/default_config.py

from pathlib import Path

from core.entities.config import (
    BenchmarkConfig,
    BenchmarkRun,
    Config,
    ModelConfig,
    OutputConfig,
    SystemInfoConfig,
)
from core.enums.model import DeviceType, ModelFamily, ModelFormat, ModelSize


def build_default_config() -> Config:
    """Создать конфиг для запуска всех комбинаций моделей и форматов."""
    models = tuple(
        ModelConfig(
            family=family.value,
            size=size.value,
        )
        for family in ModelFamily
        for size in ModelSize
    )

    return Config(
        benchmark=BenchmarkConfig(
            runs=(BenchmarkRun(models=models),),
            formats=tuple(model_format.value for model_format in ModelFormat),
            device_type=DeviceType.AUTO,
            input_size=640,
            batch_size=1,
            warmup_iterations=10,
            main_iterations=100,
            confidence_threshold=0.25,
            test_images="./data/test_images",
        ),
        system_info=SystemInfoConfig(
            collect_gpu=True,
            collect_power=True,
            collect_temperature=True,
        ),
        output=OutputConfig(
            directory=Path("./results"),
            formats=("json", "csv", "markdown"),
            use_timestamp=True,
        ),
    )
