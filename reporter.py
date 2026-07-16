import csv
import json
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from core.entities.config import OutputConfig


class Reporter:
    """Сохраняет отчеты benchmark в форматах, указанных в OutputConfig."""

    def __init__(self, output_config: OutputConfig) -> None:
        self.output_config = output_config
        self.output_directory = Path(output_config.directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def report(self, data: Any) -> None:
        """Записать одну сущность или список сущностей во все выбранные форматы."""
        for report_format in self.output_config.formats:
            match report_format.lower().strip():
                case "json":
                    self.write_json_report(data)
                case "jsonl":
                    self.write_jsonl_report(data)
                case "csv":
                    self.write_csv_report(data)
                case "md" | "markdown":
                    self.write_md_report(data)
                case _:
                    raise ValueError(
                        f"Unsupported report format: '{report_format}'. "
                        "Allowed formats are: 'json', 'jsonl', 'csv', 'md', 'markdown'."
                    )

    def write_json_report(self, data: Any) -> None:
        """Сохранить отчет в JSON-массив, дописывая новые записи к старым."""
        filename = self.output_directory / "report.json"
        previous_items = self._read_json_items(filename)
        previous_items.extend(self._to_report_items(data))

        with filename.open("w", encoding="utf-8") as file:
            json.dump(previous_items, file, ensure_ascii=False, indent=2)

    def write_jsonl_report(self, data: Any) -> None:
        """Сохранить отчет в JSONL, где каждая запись лежит на отдельной строке."""
        filename = self.output_directory / "report.jsonl"

        with filename.open("a", encoding="utf-8") as file:
            for item in self._to_report_items(data):
                file.write(json.dumps(item, ensure_ascii=False) + "\n")

    def write_csv_report(self, data: Any) -> None:
        """Сохранить отчет в CSV с плоскими колонками."""
        filename = self.output_directory / "report.csv"
        new_rows = [self._flatten_dict(item) for item in self._to_report_items(data)]

        existing_rows: list[dict[str, Any]] = []
        existing_fieldnames: list[str] = []

        if filename.exists() and filename.stat().st_size > 0:
            with filename.open("r", newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                existing_fieldnames = list(reader.fieldnames or [])
                existing_rows = list(reader)

        fieldnames = self._merge_fieldnames(existing_fieldnames, new_rows)

        with filename.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)
            writer.writerows(new_rows)

    def write_md_report(self, data: Any) -> None:
        """Сохранить отчет в Markdown как читаемые JSON-блоки."""
        filename = self.output_directory / "report.md"

        with filename.open("a", encoding="utf-8") as file:
            for item in self._to_report_items(data):
                file.write("## Report entry\n\n")
                file.write("```json\n")
                file.write(json.dumps(item, ensure_ascii=False, indent=2))
                file.write("\n```\n\n")

    def _read_json_items(self, filename: Path) -> list[dict[str, Any]]:
        if not filename.exists() or filename.stat().st_size == 0:
            return []

        with filename.open("r", encoding="utf-8") as file:
            content = json.load(file)

        if isinstance(content, list):
            return content
        if isinstance(content, dict):
            return [content]
        return []

    def _to_report_items(self, data: Any) -> list[dict[str, Any]]:
        plain_data = self._to_plain_data(data)

        if isinstance(plain_data, list):
            return [self._ensure_dict(item) for item in plain_data]
        return [self._ensure_dict(plain_data)]

    def _to_plain_data(self, value: Any) -> Any:
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Enum):
            return value.value
        if is_dataclass(value):
            return {
                field.name: self._to_plain_data(getattr(value, field.name))
                for field in fields(value)
            }
        if isinstance(value, dict):
            return {
                str(key): self._to_plain_data(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self._to_plain_data(item) for item in value]
        if hasattr(value, "__dict__"):
            return {
                key: self._to_plain_data(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        return value

    def _ensure_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {"value": value}

    def _flatten_dict(self, data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        flat_data: dict[str, Any] = {}

        for key, value in data.items():
            flat_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                flat_data.update(self._flatten_dict(value, flat_key))
            elif isinstance(value, list):
                flat_data[flat_key] = json.dumps(value, ensure_ascii=False)
            else:
                flat_data[flat_key] = value

        return flat_data

    def _merge_fieldnames(
        self,
        existing_fieldnames: list[str],
        new_rows: list[dict[str, Any]],
    ) -> list[str]:
        fieldnames = list(existing_fieldnames)

        for row in new_rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)

        return fieldnames
