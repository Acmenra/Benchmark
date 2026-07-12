# infrastructure\hardware\collectors\base.py
# потом перенесу в interfaces


from abc import ABC, abstractmethod

from core.entities.config import SystemInfoConfig

# будет контрактом для cpu, gpu, power, temperature
class BaseCollector(ABC):
    # Если строк кода много - сделать папку GPU и там уже 3 (или больше) файлов, 
    # которые реализуют этот класс (в каждом из этих двух методов создаетмся CPUStaticInfoCollector и он уже прокидывает в return)

    def __init__(self, system_info_config: SystemInfoConfig) -> None:
        self.system_info_config = system_info_config
        # потом при надобности можно еще собирать только определенные метрики 
        # MetricsConfig

    @abstractmethod 
    def get_hardware_info(self) -> ...: 
        """Возвращает статические данные о железе."""
        # Все собиратели реализованы, кроме GPU,
        # осталось создать что то по типу GPUCollector(BaseCollector) и там внести прошлую логику в get_hardware_info

    @abstractmethod
    def get_metrics(self) -> ...:
        """Возвращает метрики во время одного пробега."""
        # какие есть возвращаемые типы смотреть в core\entities\metrics.py


