# tests/test_cli.py

import sys
import pytest
from pathlib import Path

from application.cli import parse_config_path


def test_parse_config_path_valid(monkeypatch):
    test_args = ["prog", "run", "--config", "configs/test.yaml"]
    monkeypatch.setattr(sys, "argv", test_args)

    result = parse_config_path()

    assert result == Path("configs/test.yaml")


def test_missing_config(monkeypatch):
    test_args = ["prog", "run"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit):
        parse_config_path()


def test_invalid_command(monkeypatch):
    test_args = ["prog", "bad", "--config", "a.yaml"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit):
        parse_config_path()