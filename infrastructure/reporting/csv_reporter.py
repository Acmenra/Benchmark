# infrastructure/reporting/csv_reporter.py

import os
import csv
import logging
from typing import Any
from application.benchmark.reporter.base import BaseReporter
from .utils import to_report_items, flatten_dict


logger = logging.getLogger(__name__)


class CSVReporter(BaseReporter):
    """Запись в CSV с плоскими колонками. Данные дописываются, заголовки обновляются."""

    def __init__(self, output_dir: str) -> None:
        self._output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def report(self, data: Any) -> None:
        items = to_report_items(data)
        if not items:
            return

        # Определяем имя файла по классу сущности
        if isinstance(data, list) and data:
            class_name = data[0].__class__.__name__.lower()
        elif not isinstance(data, list):
            class_name = data.__class__.__name__.lower()
        else:
            return  # пустой список

        filename = os.path.join(self._output_dir, f"{class_name}_report.csv")

        # Преобразуем в плоские словари
        flat_items = [flatten_dict(item) for item in items]

        # Читаем существующие строки, если файл есть
        existing_rows = []
        existing_fieldnames = []
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_fieldnames = list(reader.fieldnames or [])
                existing_rows = list(reader)

        # Объединяем fieldnames
        all_fieldnames = list(existing_fieldnames)
        for row in flat_items:
            for key in row.keys():
                if key not in all_fieldnames:
                    all_fieldnames.append(key)

        # Перезаписываем файл с новым заголовком и всеми строками
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)
            writer.writerows(flat_items)