# application/benchmark/reporter/reporter.py

import logging
from typing import List, Dict, Any
from application.benchmark.reporter import BaseReporter


logger = logging.getLogger(__name__)


class Reporter:
    """
    Orchestrator that invokes all enabled format-specific reporters.

    Acts as a facade over multiple concrete reporter implementations (CSV, JSON, Markdown, etc.),
    allowing the benchmark pipeline to output results in multiple formats simultaneously.
    The orchestrator validates that all requested formats are supported before execution,
    ensuring fail-fast behavior for misconfigured output settings.

    Key design decisions (contracts):
    - Reporters are injected via dependency injection (dict of format -> reporter instance)
    - Enabled formats are normalized to lowercase and stripped of whitespace
    - Unsupported formats raise ValueError immediately (fail-fast principle)
    - Reporters are executed sequentially in the order specified by enabled_formats

    Designed for seamless integration with the benchmark pipeline:
    - Multi-format output generation (CSV + JSON + Markdown)
    - Configurable output formats via YAML configuration
    - Extensible architecture for adding new report formats

    Attributes:
        _reporters (Dict[str, BaseReporter]): Dictionary mapping format names to reporter instances.
        _enabled_formats (List[str]): List of enabled output formats (normalized to lowercase).

    Note:
        - All reporters must implement the BaseReporter interface
        - Format names are case-insensitive (normalized internally)
        - Reporters are executed in the order specified by enabled_formats
    """

    def __init__(self,
                 reporters: Dict[str, BaseReporter],
                 enabled_formats: List[str]) -> None:
        """
        Initializes the reporter orchestrator with format-specific reporters.

        Args:
            reporters (Dict[str, BaseReporter]): Dictionary mapping format names (e.g., 'csv', 'json')
                to reporter instances. Keys should be lowercase format identifiers.
            enabled_formats (List[str]): List of output formats to generate. Format names are
                normalized to lowercase and stripped of whitespace.

        Note:
            - Reporters are stored as-is (no validation of reporter instances)
            - Enabled formats are normalized for case-insensitive matching
            - Empty enabled_formats list results in no output generation
        """
        self._reporters = reporters
        self._enabled_formats = [fmt.lower().strip() for fmt in enabled_formats]

    def report(self,
               data: Any) -> None:
        """
        Generates reports in all enabled formats for the given data.

        Iterates through enabled formats and invokes the corresponding reporter for each.
        Reporters are executed sequentially in the order specified by enabled_formats.

        Args:
            data (Any): Benchmark results to report. Typically a list of ModelBenchmarkResult
                instances or a single result object.

        Raises:
            ValueError: If any enabled format is not supported (not present in reporters dict).
                The error message includes the unsupported format and list of available formats.

        Note:
            - Fail-fast validation: all formats are validated before any reporter is invoked
            - Sequential execution: reporters are called one by one (no parallel execution)
            - Partial success: if a reporter fails, subsequent reporters may not be invoked
              (depends on reporter implementation)
        """
        for fmt in self._enabled_formats:
            reporter = self._reporters.get(fmt)
            if not reporter:
                raise ValueError(
                    f"Unsupported report format: '{fmt}'. "
                    f"Available formats are: {list(self._reporters.keys())}"
                )
            reporter.report(data)