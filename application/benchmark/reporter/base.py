# application/benchmark/reporter/base.py

import logging
from typing import Any
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class BaseReporter(ABC):
    """
    Abstract base class for all format-specific reporters.

    Defines the contract that any reporter (CSV, JSON, Markdown, etc.)
    must implement to persist benchmark results. Provides a unified interface
    for data serialization, ensuring backend-agnostic and format-agnostic reporting.

    Key design decisions (contracts):
    - All reporters must implement `report()` accepting either a single entity or a list
    - Reporters should handle file I/O, directory creation, and timestamp formatting
    - Reporters must be stateless between calls (no internal buffering across invocations)
    - Error handling should be explicit (raise exceptions rather than silently failing)

    Designed for seamless integration with the benchmark pipeline:
    - Aggregating results from multiple benchmark runs
    - Exporting performance metrics for downstream analysis
    - Generating human-readable summaries for stakeholder review

    Note:
        - Subclasses must implement the `report()` method
        - Reporters should validate input data structure before serialization
        - File paths should be resolved relative to the configured output directory
    """

    @abstractmethod
    def report(self, data: Any) -> None:
        """
        Persist benchmark data to the target format (file, database, etc.).

        Args:
            data (Any): Benchmark result(s) to report. Can be a single
                        `ModelBenchmarkResult` instance or a list of results.

        Raises:
            IOError: If file writing fails due to permissions or disk space.
            ValueError: If data structure is invalid or incompatible with the format.

        Note:
            - Implementations should handle both single items and lists uniformly
            - File creation and directory structure should be managed internally
            - Timestamps should be formatted according to the configured output settings
        """
        pass