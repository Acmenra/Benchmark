# infrastructure/exceptions/quantization/errors.py

import logging
from infrastructure.exceptions.base import ModelError


logger = logging.getLogger(__name__)


class ConfigError(ValueError):
    """Configuration validation error."""