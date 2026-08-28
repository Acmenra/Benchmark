# infrastructure/exceptions/config/__init__.py

import logging

from infrastructure.exceptions import ConfigError


logger = logging.getLogger(__name__)


__all__ = [
    'ConfigError'
]