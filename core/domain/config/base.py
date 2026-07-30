# core/domain/config/base.py

import logging


logger = logging.getLogger(__name__)


class BaseConfig:
    """
    Base marker class for all configuration entities in the benchmark domain.

    This class serves as a foundational type hint and structural contract for
    all configuration dataclasses. It ensures that all config objects share
    a common lineage, making type checking and validation pipelines more robust.

    Key design decisions:
    - Subclasses MUST be decorated with `@dataclass(slots=True, frozen=True)`
      to guarantee immutability and memory efficiency.
    - Provides a unified base for type introspection and validation.

    Note:
        - This class itself is not a dataclass; it is intended to be inherited
          by concrete, frozen dataclasses.
        - Do not instantiate this class directly.
    """
    pass
