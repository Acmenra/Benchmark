# core/domain/config/base.py

import logging
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BaseConfig:
    """Базовый класс для всех конфигурационных сущностей."""
