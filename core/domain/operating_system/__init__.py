# core/domain/operating_system/__init__.py

import logging
from core.domain.operating_system.operating_system import OSInfo


logger = logging.getLogger(__name__)


__all__ = [
    'OSInfo'
]


__version__ = "0.0.0.1"