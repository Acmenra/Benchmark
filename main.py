# main.py
import logging
from application.benchmark.runner import BenchmarkRunner
from application.cli import parse_config_path
from infrastructure.config.default_config import build_default_config
from infrastructure.config.config_reader import read_yaml
from infrastructure.hardware.collector import HardwareCollector
from application.benchmark.reporter import Reporter
from infrastructure.reporting import CSVReporter, JSONReporter

logger = logging.getLogger(__name__)


def main() -> None:
    config_path = parse_config_path()
    config = build_default_config() if config_path is None else read_yaml(config_path)

    output_config = config.output

    # Создаём словарь репортеров по форматам
    reporters = {}
    if "csv" in output_config.formats:
        reporters["csv"] = CSVReporter(output_config.directory)
    if "json" in output_config.formats:
        reporters["json"] = JSONReporter(output_config.directory)
    # При необходимости можно добавить другие форматы (md, jsonl)

    enabled_formats = [f for f in output_config.formats if f in reporters]  # только те, что поддерживаем
    reporter = Reporter(reporters, enabled_formats)

    if config.system_info:
        collector = HardwareCollector(config.system_info)
        system_info = collector.get_system_info()
        reporter.report(system_info)

    if config.benchmark:
        runner = BenchmarkRunner(config.benchmark)
        results = runner.run_suite()
        reporter.report(results)


if __name__ == '__main__':
    main()