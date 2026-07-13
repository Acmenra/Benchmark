# infrastructure/hardware/collectors/gpu.py
from typing import Any

from core.entities.hardware import GPUInfo

# смотреть hardware/entities.py,
# примерная реализация лежит в hardware/CHECK_THIS.PY

# TODO сделать class GPUCollector(BaseCollector):

class GPUCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        # some loads

    def info(self) -> GPUInfo:
        ...

    def tmp(self) -> Any:
        ...

    def frq(self) -> Any:
        ...

    def prsnt(self) -> Any:
        ...

    def mem(self) -> Any:
        ...


# 1. Прогружаемся + базовые значения
# 2. Делаем private _method() -> достаём "базовую" информацию о GPU
# 3. По вызову метода .info() -> "GPUInfo" - можем получить текущую инфу о температуре ГПУ
# 4. По вызову метода .tmp() (определить, что возвращает) - можем получить текущую инфу о температуре ГПУ
# 5. По вызову метода .frq() (определить, что возвращает) - можем получить текущую инфу о частоте ГПУ
# 6. По вызову метода .mem() (определить, что возвращает) - можем получить текущую инфу о памяти занятой НАШИМ ПО в ГПУ

def collect_gpu() -> GPUInfo:
    ...