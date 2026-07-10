import csv
import os
from typing import Any
from application.benchmark.reporter.base import BaseReporter


class CSVReporter(BaseReporter):
    """Реализация BaseReporter для записи результатов в CSV."""

    def __init__(self, output_dir: str = ".") -> None:
        self._output_dir = output_dir

    def report(self, entity: Any) -> None:
        data_dict = vars(entity)

        class_name = entity.__class__.__name__.lower()
        filename = os.path.join(self._output_dir, f"{class_name}_report.csv")

        file_exists = os.path.isfile(filename) and os.path.getsize(filename) > 0

        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data_dict.keys())

            if not file_exists:
                writer.writeheader()

            writer.writerow(data_dict)