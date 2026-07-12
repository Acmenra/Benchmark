# application/cli.py

from argparse import ArgumentParser
from pathlib import Path


def parse_config_path() -> Path:
    parser = ArgumentParser()

    parser.add_argument(
        "command",
        choices=["run"],
    )

    parser.add_argument(
        "--config",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    return args.config