# config.py

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class ModelConfig:
    # при одной модели можно задавать несколько размеров
    # sizes: [n, s, ...], 
    # тогда все они должны быть выделены как отдельные ModelConfig
    #
    # Если за один прогон несколько моделей, 
    # то можно лишь указать один размер для каждой модели (валидация)
    size: str
    family: str

    
# Один прогон моделей 
# Если len(models) == 1 - одна модель прогоняется 
# Если len(models) > 1 - несколько моделей за один раз
@dataclass(slots=True, frozen=True)
class BenchmarkRun:
    models: list[ModelConfig]


@dataclass(slots=True, frozen=True)
class BenchmarkConfig:
    runs: list[BenchmarkRun]
    ...

@dataclass(slots=True, frozen=True)
class SystemInfoConfig:
    collect_gpu: bool
    collect_power: bool
    collect_temperature: bool


@dataclass(slots=True, frozen=True)
class OutputConfig:
    directory: Path
    formats: list[str] # [json, csv, md]
    use_timestamp: bool


@dataclass(slots=True, frozen=True)
class Config:
    benchmark: BenchmarkConfig | None
    system_info: SystemInfoConfig | None
    output: OutputConfig 
    


def read_yaml(path: Path) -> Config:
    ...

    

# примерная конструкция yaml

# # configs/default.yaml
# benchmark:
#  runs:
#   - models:
#     - family: yolov8
#       sizes: [n, s, m]
#     - family: yolov11
#       sizes: [n, s]
#   - models:
#     - family: yolov8
#       sizes: [n, s, m]  
#   formats: [pytorch, onnx, tensorrt, openvino]
  
#   input_size: 640
#   batch_size: 1
#   warmup_iterations: 10
#   main_iterations: 100
#   confidence_threshold: 0.25
  
#   test_images: "./data/test_images/"

# output:
#   directory: "./results/"
#   formats: [json, csv, markdown]
#   timestamp: true

# system_info:
#   collect_gpu: true
#   collect_power: true
#   collect_temperature: true