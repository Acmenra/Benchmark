import sys
import logging

from application.cli import parse_args
from core.domain.config import SystemInfoConfig
from infrastructure.config.default_config import build_default_config
from infrastructure.config.config_reader import read_yaml
from application.benchmark.reporter import Reporter
from infrastructure.hardware.collectors.base import BaseHardwareCollector
from infrastructure.reporting import CSVReporter, JSONReporter
from infrastructure.hardware.collector import HardwareCollector
from application.benchmark.runner import BenchmarkRunner

logger = logging.getLogger(__name__)

def print_system_banner(system_info) -> None:
    # ... (твой существующий код баннера без изменений) ...
    pass

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 1. Парсим аргументы
    args = parse_args()
    config_path = args.config
    info_only = args.info  # <-- Ловим наш новый флаг

    # 2. Загружаем конфиг
    config = build_default_config() if config_path is None else read_yaml(config_path)

    # 3. Собираем и печатаем инфо о системе
    system_info = None
    if config.system_info:
        collector = HardwareCollector(config.system_info)
        system_info = collector.get_system_info()
        print_system_banner(system_info)

        # 🚨 ГЛАВНОЕ: Если передан флаг --info, выходим сразу после печати!
        if info_only:
            logger.info("Режим просмотра информации. Завершение работы без запуска бенчмарка.")
            sys.exit(0)

    # 4. Настраиваем репортеры (только если мы НЕ в режиме --info)
    output_config = config.output
    reporters = {}
    if "csv" in output_config.formats:
        reporters["csv"] = CSVReporter(output_config.directory)
    if "json" in output_config.formats:
        reporters["json"] = JSONReporter(output_config.directory)

    enabled_formats = [f for f in output_config.formats if f in reporters]
    reporter = Reporter(reporters, enabled_formats)

    # 5. Запуск бенчмарка
    if config.benchmark:
        runner = BenchmarkRunner(
            benchmark_config=config.benchmark,
            system_info_config=config.system_info
        )
        for result in runner.run_suite():
            reporter.report(result)

if __name__ == '__main__':
    main()