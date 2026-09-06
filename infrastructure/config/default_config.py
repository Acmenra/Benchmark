# infrastructure/config/default_config.py

import logging
from pathlib import Path

from core.enums.model import DeviceType, ModelFamily, ModelFormat, ModelSize, QuantizationLevel, TaskType
from core.domain.config import Config, ModelConfig, BenchmarkConfig, BenchmarkCase, SystemInfoConfig, ReportConfig


logger = logging.getLogger(__name__)


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

    return Config(benchmark=BenchmarkConfig(runs=(BenchmarkCase(models=models),),
                                            devices=(DeviceType.AUTO,),
                                            models_dir=Path("./models"),
                                            formats=tuple(model_format.value for model_format in ModelFormat),
                                            quantization=(QuantizationLevel.FP32.value,),
                                            task_type=TaskType.DETECT,
                                            input_size=640,
                                            batch_size=1,
                                            warmup_iterations=10,
                                            main_iterations=100,
                                            confidence_threshold=0.25,
                                            test_images="./data/test_images"),
                  system_info=SystemInfoConfig(collect_cpu=True,
                                               collect_gpu=True,
                                               collect_power=True,
                                               collect_temperature=True),
                  output=ReportConfig(directory=Path("./results"),
                                      formats=("json", "csv", "markdown"),
                                      use_timestamp=True))
