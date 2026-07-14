# infrastructure/hardware/collectors/gpu.py

import logging

logger = logging.getLogger(__name__)

from typing import Any

from core.entities.hardware import GPUInfo
from core.entities.metrics import DataPoint
from infrastructure.hardware.collectors.base import BaseCollector


# TODO сделать class GPUCollector(BaseCollector):

class GPUCollector(BaseCollector):
    def __init__(self):
        # some loads
        ...

    def info(self) -> GPUInfo:
        ...

    def tmp(self) -> DataPoint:
        ...

    def frq(self) -> DataPoint:
        ...

    def prsnt(self) -> Any:
        ...

    def mem(self) -> DataPoint:
        ...

    def power(self) -> DataPoint:
        ...

# 1. Прогружаемся + базовые значения
# 2. Делаем private _method() -> достаём "базовую" информацию о GPU
# 3. По вызову метода .info() -> "GPUInfo" - можем получить текущую инфу о температуре ГПУ
# 4. По вызову метода .tmp() (определить, что возвращает) - можем получить текущую инфу о температуре ГПУ
# 5. По вызову метода .frq() (определить, что возвращает) - можем получить текущую инфу о частоте ГПУ
# 6. По вызову метода .mem() (определить, что возвращает) - можем получить текущую инфу о памяти занятой НАШИМ ПО в ГПУ
