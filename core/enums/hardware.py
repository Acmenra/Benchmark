# hardware/enums.py

from enum import StrEnum


# заменить потом на PlatformType
class HardwarePlatform(StrEnum):
    UNKNOWN = "unknown"

    PC = "pc"

    RASPBERRY_PI = "raspberry_pi"
    ORANGE_PI = "orange_pi"
    JETSON = "jetson"
    ORIN = "orin"


# class PlatformType(Enum):
#     DESKTOP = 'desktop'
#     JETSON = 'jetson'
#     RASPBERRY_PI = 'raspberry_pi'
#     INTEL_NUC = 'intel_nuc'
#     HAILO = 'hailo'
#     UNKNOWN = 'unknown'  # fallback для неопознанных систем