from dataclasses import dataclass

from config import SystemInfoConfig
from hardware.cpu import collect_cpu


# типы атрибутов тоже датаклассы (или нет), пример: config.py
@dataclass(slots=True, frozen=True)
class SystemInfo:
    # cpu: ... | None
    # gpu: ... | None 
    # temperature: ... | None
    # power: ...| None
    # os: ... | None
    ...


class HardwareCollector:
    def __init__(self, config: SystemInfoConfig) -> None:
        ...

    def get_system_info(self) -> SystemInfo:
        ...