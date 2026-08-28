# infrastructure/reporting/json_reporter.py

import os
import json
import logging
from typing import Any
from infrastructure.utils.utils import to_report_items
from application.benchmark.reporter.base import BaseReporter


logger = logging.getLogger(__name__)


class JSONReporter(BaseReporter):
    """Запись в JSON-массив. Данные дописываются в конец массива."""

    def __init__(self, output_dir: str) -> None:
        self._output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def report(self, data: Any) -> None:
        items = to_report_items(data)
        if not items:
            return

        # Определяем имя файла
        if isinstance(data, list) and data:
            class_name = data[0].__class__.__name__.lower()
        elif not isinstance(data, list):
            class_name = data.__class__.__name__.lower()
        else:
            return

        filename = os.path.join(self._output_dir, f"{class_name}_report.json")

        # Читаем существующий массив
        existing = []
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        existing = content
                    elif isinstance(content, dict):
                        existing = [content]
                    # иначе считаем массив пустым
            except json.JSONDecodeError:
                # Файл повреждён – начинаем заново
                existing = []

        # Добавляем новые записи
        existing.extend(items)

        # Перезаписываем
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)