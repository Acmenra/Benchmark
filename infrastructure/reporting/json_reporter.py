# infrastructure/reporting/json_reporter.py

import os
import json
import logging
from typing import Any
from infrastructure.utils.utils import to_report_items
from application.benchmark.reporter.base import BaseReporter


logger = logging.getLogger(__name__)


class JSONReporter(BaseReporter):
    """
    Hierarchical persistence with resilient array extension.

    This reporter appends new benchmark results to an existing JSON array.
    It includes built-in corruption recovery: if the existing JSON file is
    malformed, it safely resets the array rather than crashing the suite.
    """

    def __init__(self, output_dir: str) -> None:
        """
        Initializes the JSON reporter and ensures the output directory exists.

        Args:
            output_dir: The target directory for saving JSON reports.
        """
        self._output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def report(self, data: Any) -> None:
        """
        Persists benchmark data to a JSON file, appending to existing results.

        Args:
            data: A single domain entity or a list of entities to be reported.
        """
        items = to_report_items(data)
        if not items:
            return

        if isinstance(data, list) and data:
            class_name = data[0].__class__.__name__.lower()
        elif not isinstance(data, list):
            class_name = data.__class__.__name__.lower()
        else:
            return

        filename = os.path.join(self._output_dir, f"{class_name}_report.json")

        existing = []
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        existing = content
                    elif isinstance(content, dict):
                        existing = [content]
            except json.JSONDecodeError:
                existing = []

        existing.extend(items)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)