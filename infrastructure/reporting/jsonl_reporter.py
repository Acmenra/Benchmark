import json
import os
from typing import Any
from application.benchmark.reporter.base import BaseReporter


class JSONLReporter(BaseReporter):
    """Реализация BaseReporter для записи результатов в формате JSONL."""

    def __init__(self, output_dir: str = ".") -> None:
        self._output_dir = output_dir

    def report(self, entity: Any) -> None:
        data_dict = vars(entity)

        class_name = entity.__class__.__name__.lower()
        filename = os.path.join(self._output_dir, f"{class_name}_report.jsonl")

        with open(filename, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data_dict, ensure_ascii=False) + '\n')