# infrastructure/hardware/collectors/gpu.py

from core.entities.hardware import GPUInfo

# смотреть hardware/entities.py,
# примерная реализация лежит в hardware/CHECK_THIS.PY

def collect_gpu() -> GPUInfo:
    ...