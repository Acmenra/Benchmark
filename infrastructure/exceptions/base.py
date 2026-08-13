# infrastructure/exceptions/base.py

import logging


logger = logging.getLogger(__name__)


class RaBenchmarkException(Exception):
    """
    Root exception for all benchmark-related errors.

    Raised when an unrecoverable error occurs within the benchmark pipeline
    that is specific to the application logic (e.g., invalid config, missing dataset).
    """
    pass


class ConfigError(RaBenchmarkException):
    """
    Exception raised for configuration validation or parsing errors.

    Raised when:
        - The YAML configuration file is malformed or missing required fields.
        - Provided values fail Pydantic schema validation (e.g., invalid device type).
    """
    pass


class DatasetError(RaBenchmarkException):
    """
    Exception raised for dataset loading or validation errors.

    Raised when:
        - The specified dataset path does not exist or is not a directory.
        - The dataset lacks required files (e.g., `data.yaml`, `images/`).
    """
    pass


class ModelError(RaBenchmarkException):
    """
    Base exception for all model-related errors (loading, inference, export, quantization).

    Subclasses should be used to specify the exact stage of the model pipeline
    where the failure occurred, enabling granular error handling in the runner.
    """
    pass