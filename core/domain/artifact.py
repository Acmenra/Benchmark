# core/domain/artifact.py

import logging
from pathlib import Path
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ResolvedModelArtifact:
    """
    Represents the fully resolved model artifact after configuration resolution.

    This class serves as the immutable result of the model resolution process,
    containing the exact file path to the model and its specific quantization level.
    It ensures that downstream components (e.g., benchmark runners, inference backends)
    receive a strictly typed, predictable, and unmodifiable artifact reference.

    Key design decisions:
    - Immutability (`frozen=True`): Prevents accidental mutation of the artifact path
      or quantization level after resolution.
    - Memory efficiency (`slots=True`): Reduces memory overhead, which is critical
      when handling multiple artifacts in long-running benchmark suites.
    - Strict typing: Enforces `Path` for the file location and `str` for the
      quantization level.

    Attributes:
        path (Path): The absolute or relative path to the resolved model file.
        quantization (str): The quantization level of the artifact (e.g., 'fp32', 'fp16', 'int8').
    """
    path: Path
    quantization: str