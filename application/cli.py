# application/cli.py

import logging

from argparse import ArgumentParser, Namespace
from pathlib import Path


logger = logging.getLogger(__name__)


def parse_args() -> Namespace:
    """
    Parses command-line arguments for the benchmark suite.

    Configures the `argparse` parser to handle execution commands,
    configuration file paths, and system information queries. This
    function serves as the boundary between user input and the
    application's internal configuration routing.

    Supported Commands:
        - `run`: Initiates the benchmark execution pipeline.

    Supported Flags:
        - `--config`: Path to a custom YAML configuration file.
        - `--info`: Outputs system hardware/OS information and exits
                    without running the benchmark.

    Returns:
        Namespace: An argparse Namespace object containing the parsed
                   arguments (`command`, `config`, `info`).

    Note:
        - The parser is configured with `choices=["run"]` to enforce
          strict command validation at the CLI level.
        - The `--config` argument defaults to `None`, allowing the
          application layer to fallback to a default configuration
          if no custom path is provided.
    """
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