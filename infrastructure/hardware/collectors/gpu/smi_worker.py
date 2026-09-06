# infrastructure/hardware/collectors/gpu/smi_worker.py

import shutil
import logging
import subprocess
from typing import Any, Optional

from core.domain.hardware import GPUInfo
from infrastructure.utils.utils import to_float, to_int


logger = logging.getLogger(__name__)


class SMIWorker:
    """
    Self-contained fallback adapter for the `nvidia-smi` CLI tool.

    Key design decisions:
    - Instant availability check: Uses `shutil.which` during initialization to
      avoid repeated filesystem lookups.
    - Strict timeouts: All subprocess calls are bounded by a 3-second timeout
      to prevent the benchmark runner from hanging on unresponsive drivers.
    - Optimized querying: Fetches multiple metrics in a single CSV-formatted
      CLI call to minimize subprocess overhead.
    """

    def __init__(self) -> None:
        """
        Initializes the worker and checks if `nvidia-smi` is in the system PATH.
        """
        self._available = shutil.which("nvidia-smi") is not None

    def is_available(self) -> bool:
        """
        Checks if the `nvidia-smi` CLI tool is accessible.

        Returns:
            bool: True if the tool is found in the system PATH.
        """
        return self._available

    def get_info(self) -> GPUInfo:
        """
        Retrieves static hardware specifications via a single `nvidia-smi` query.

        Returns:
            GPUInfo: Populated with GPU name, total VRAM, and driver version.
                     Returns an empty `GPUInfo` if the query fails.
        """
        values = self._query("name,memory.total,driver_version")
        if not values or len(values) < 3:
            return GPUInfo(name=None,
                           memory_mb=None,
                           driver_version=None,
                           cuda_version=None)
        return GPUInfo(name=values[0],
                       memory_mb=to_int(values[1]),
                       driver_version=values[2],
                       cuda_version=None)

    def get_float(self,
                  query: str) -> Optional[float]:
        """
        Executes a query and attempts to parse the first result as a float.

        Args:
            query: The `nvidia-smi` metric to query (e.g., 'utilization.gpu').

        Returns:
            float | None: The parsed numeric value, or `None` if parsing fails.
        """
        values = self._query(query)
        return to_float(values[0]) if values else None

    def _query(self,
               query: str) -> list[str] | None:
        """
        Internal method to execute the `nvidia-smi` subprocess.

        Args:
            query: Comma-separated list of metrics to retrieve.

        Returns:
            list[str] | None: A list of string values corresponding to the queried metrics,
                              or `None` if the command fails or times out.
        """
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