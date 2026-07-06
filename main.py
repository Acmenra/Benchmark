from pathlib import Path

from cli import parse_config_path
from config import read_yaml


def main() -> None:
    config_path = parse_config_path()
    config = read_yaml(config_path)



    match ...:
        case _:
            ...




if __name__ == '__main__':
    main()