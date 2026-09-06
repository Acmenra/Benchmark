# infrastructure/hardware/collectors/pwr/power.py

import re
import time
import logging
import platform
import subprocess
from pathlib import Path

from infrastructure.utils.utils import read_int

logger = logging.getLogger(__name__)


def collect_cpu_power_watts() -> float | None:
    """
    Main entry point for CPU power retrieval.

    Dispatches to the appropriate OS-specific power collection method based
    on the current platform.

    Returns:
        float | None: The current CPU power consumption in Watts, or `None`
                      if the platform is unsupported or the reading fails.
    """
    system = platform.system()

    if system == "Darwin":
        return _collect_macos_cpu_power_watts()
    if system == "Linux":
        return _collect_linux_rapl_cpu_power_watts()

    return None


def _collect_macos_cpu_power_watts() -> float | None:
    """
    Retrieves CPU power on macOS via the `powermetrics` CLI tool.

    Executes the tool with a strict 5-second timeout to prevent benchmark hangs.
    Designed specifically for Apple Silicon and modern macOS environments.

    Returns:
        float | None: The parsed power value in Watts, or `None` if the
                      subprocess fails or returns an error code.
    """
    try:
        result = subprocess.run(
            ["powermetrics", "-n", "1", "--samplers", "cpu_power"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None

    return _parse_macos_cpu_power(result.stdout)


def _parse_macos_cpu_power(output: str) -> float | None:
    """
    Parses the `powermetrics` stdout to extract CPU power.

    Uses regular expressions to find "CPU Power" or "Processor Power" values.
    Automatically handles unit conversion from milliwatts (mW) to Watts (W).

    Args:
        output: The raw stdout string from the `powermetrics` command.

    Returns:
        float | None: The converted power value in Watts, validated by
                      `_is_valid_power()`, or `None` if no match is found.
    """
    patterns = (
        r"CPU Power:\s+([\d.]+)\s+mW",
        r"CPU Power:\s+([\d.]+)\s+W",
        r"Processor Power:\s+([\d.]+)\s+mW",
        r"Processor Power:\s+([\d.]+)\s+W",
    )

    for line in output.splitlines():
        for pattern in patterns:
            match = re.search(pattern, line)
            if match is None:
                continue

            value = float(match.group(1))
            if "mW" in pattern:
                value = value / 1000.0

            if _is_valid_power(value):
                return value

    return None


def _collect_linux_rapl_cpu_power_watts() -> float | None:
    """
    Retrieves CPU power on Linux via Intel RAPL (Running Average Power Limit).

    Calculates instantaneous power by reading the `energy_uj` (microjoules)
    counter twice with a 0.1-second delay. Power is calculated as:
    `Delta Energy (Joules) / Delta Time (seconds)`.

    Includes safe handling for hardware counter overflow (wrap-around).

    Returns:
        float | None: The calculated power in Watts, or `None` if the RAPL
                      path is missing, unreadable, or the counter overflows.
    """
    energy_path = _find_rapl_energy_path()
    if energy_path is None:
        return None

    energy_before = read_int(energy_path)
    if energy_before is None:
        return None

    measured_at = time.perf_counter()
    time.sleep(0.1)

    energy_after = read_int(energy_path)
    if energy_after is None:
        return None

    elapsed_seconds = time.perf_counter() - measured_at
    if elapsed_seconds <= 0:
        return None

    # RAPL хранит энергию в микроджоулях. Watts = Joules / seconds.
    energy_delta_uj = energy_after - energy_before
    if energy_delta_uj < 0:
        # Счетчик может переполниться; такой снимок пропускаем.
        return None

    power_watts = (energy_delta_uj / 1_000_000.0) / elapsed_seconds
    if _is_valid_power(power_watts):
        return power_watts

    return None


def _find_rapl_energy_path() -> Path | None:
    """
    Locates the `energy_uj` file for package-level Intel RAPL.

    Scans `/sys/class/powercap/intel-rapl*/` to find a valid energy counter.

    Returns:
        Path | None: The resolved path to the energy counter file, or `None`
                     if the powercap directory is missing or empty.
    """
    powercap_root = Path("/sys/class/powercap")
    if not powercap_root.exists():
        return None

    candidates = sorted(powercap_root.glob("intel-rapl*/energy_uj"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def _is_valid_power(power_watts: float) -> bool:
    """
    Sanity check for power readings.

    Validates that the power value is numeric and falls within a physically
    reasonable range for computing hardware, filtering out erroneous or
    uninitialized sensor readings.

    Args:
        power_watts: The calculated power value.

    Returns:
        bool: `True` if `0 <= power_watts < 1000`.
    """
    return isinstance(power_watts, (int, float)) and 0 <= power_watts < 1000
