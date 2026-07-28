# infrastructure/hardware/collectors/gpu/smi_worker.py

import shutil
import logging
import subprocess
from typing import Any

from core.domain.hardware import GPUInfo
from infrastructure.utils.utils import to_float, to_int


logger = logging.getLogger(__name__)



class SMIWorker:
    """Самодостаточный адаптер для работы с CLI nvidia-smi (fallback)."""

    def __init__(self) -> None:
        self._available = shutil.which("nvidia-smi") is not None

    def is_available(self) -> bool:
        return self._available

    def get_info(self) -> GPUInfo:
        values = self._query("name,memory.total,driver_version")
        if not values or len(values) < 3:
            return GPUInfo(name=None, memory_mb=None, driver_version=None, cuda_version=None)
        return GPUInfo(name=values[0], memory_mb=to_int(values[1]), driver_version=values[2], cuda_version=None)

    def get_float(self, query: str) -> float | None:
        values = self._query(query)
        return to_float(values[0]) if values else None

    def _query(self, query: str) -> list[str] | None:
        if not self._available:
            return None
        try:
            result = subprocess.run(
                ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits", "-i", "0"],
                check=True, capture_output=True, text=True, timeout=3,
            )
            first_line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
            return [v.strip() for v in first_line.split(",")] if first_line else None
        except Exception:
            return None