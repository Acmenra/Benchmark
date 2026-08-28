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
    """Вернуть текущую мощность CPU в ваттах, если платформа это позволяет."""
    system = platform.system()

    if system == "Darwin":
        return _collect_macos_cpu_power_watts()
    if system == "Linux":
        return _collect_linux_rapl_cpu_power_watts()

    return None


def _collect_macos_cpu_power_watts() -> float | None:
    """Получить мощность CPU на macOS через powermetrics."""
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
    """Достать CPU Power из вывода powermetrics."""
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
    """Получить мощность CPU на Linux через Intel RAPL energy_uj."""
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
    """Найти energy_uj для package-level Intel RAPL."""
    powercap_root = Path("/sys/class/powercap")
    if not powercap_root.exists():
        return None

    candidates = sorted(powercap_root.glob("intel-rapl*/energy_uj"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def _is_valid_power(power_watts: float) -> bool:
    """Проверить, что мощность выглядит как реальное значение."""
    return isinstance(power_watts, (int, float)) and 0 <= power_watts < 1000
