# infrastructure/reporting/csv_reporter.py

import os
import csv
import logging
from typing import Any
from application.benchmark.reporter.base import BaseReporter
from infrastructure.utils.utils import to_report_items, flatten_dict


logger = logging.getLogger(__name__)


class CSVReporter(BaseReporter):
    """
    Tabular persistence with dynamic schema evolution.

    This reporter converts nested domain objects into flat dictionaries and
    writes them to a CSV file. Its most powerful feature is header merging:
    if a new benchmark run introduces a new metric (a new key), the reporter
    reads the existing CSV, unions the headers, and rewrites the file, ensuring
    no data is lost and columns remain aligned.
    """

    def __init__(self,
                 output_dir: str) -> None:
        """
        Initializes the CSV reporter and ensures the output directory exists.

        Args:
            output_dir: The target directory for saving CSV reports.
        """
        self._output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def report(self, data: Any) -> None:
        """
        Persists benchmark data to a CSV file with dynamic schema handling.

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

        filename = os.path.join(self._output_dir, f"{class_name}_report.csv")
        flat_items = [flatten_dict(item) for item in items]

        existing_rows = []
        existing_fieldnames = []
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_fieldnames = list(reader.fieldnames or [])
                existing_rows = list(reader)

        all_fieldnames = list(existing_fieldnames)
        for row in flat_items:
            for key in row.keys():
                if key not in all_fieldnames:
                    all_fieldnames.append(key)

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)
            writer.writerows(flat_items)