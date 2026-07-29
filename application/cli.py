# application/cli.py

import logging

from argparse import ArgumentParser, Namespace
from pathlib import Path


logger = logging.getLogger(__name__)


def parse_args() -> Namespace:
    """Парсит аргументы командной строки и возвращает объект Namespace."""
    parser = ArgumentParser(description="Edge AI Benchmark Suite")

    parser.add_argument(
        "command",
        choices=["run"],
        help="Команда для выполнения (пока поддерживается только 'run')"
    )

    parser.add_argument(
        "--config",
        type=Path,
        required=False,
        default=None,
        help="Путь к YAML файлу конфигурации"
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="Вывести информацию о системе и завершить работу (без запуска бенчмарка)"
    )

    return parser.parse_args()