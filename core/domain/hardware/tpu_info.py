# core/domain/hardware/tpu_info.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class TPUInfo:
    ...