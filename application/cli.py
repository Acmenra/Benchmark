# application/cli.py

import logging

from argparse import ArgumentParser
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_config_path() -> Path | None:
    parser = ArgumentParser()

    parser.add_argument(
        "command",
        choices=["run"],
    )

    parser.add_argument(
        "--config",
        type=Path,
        required=False,
        default=None,
    )

    args = parser.parse_args()

    return args.config
