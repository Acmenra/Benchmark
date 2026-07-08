# hardware/enums.py

from enum import StrEnum


class HardwarePlatform(StrEnum):
    UNKNOWN = "unknown"

    PC = "pc"

    RASPBERRY_PI = "raspberry_pi"
    ORANGE_PI = "orange_pi"
    JETSON = "jetson"
    ORIN = "orin"