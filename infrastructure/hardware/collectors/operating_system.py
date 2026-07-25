# infrastructure/hardware/collectors/operating_system.py

import logging
import platform
from core.domain.operating_system import OSInfo
from infrastructure.utils.utils import empty_to_none


logger = logging.getLogger(__name__)


class OSCollector:

    def collect(self) -> OSInfo:
        """
        Сбор базовой информации об операционной системе.
        Набор полей зависит от текущего OSInfo.
        """
        return OSInfo(system=empty_to_none(platform.system()),
                      release=empty_to_none(platform.release()),
                      kernel=empty_to_none(platform.version()),
                      architecture=empty_to_none(platform.machine()))