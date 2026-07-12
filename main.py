# main.py

from application.benchmark.runner import BenchmarkRunner
from application.cli import parse_config_path
from infrastructure.config.config_reader import read_yaml
from infrastructure.hardware.collector import HardwareCollector
from reporter import Reporter


def main() -> None:
    config_path = parse_config_path()
    config = read_yaml(config_path)
    
    reporter = Reporter(config.output)

    if config.system_info:
        collector = HardwareCollector(config.system_info)
        system_info = collector.get_system_info()
        reporter.report(system_info) # По итогу имеем "отчет" с инфой о железе

    if config.benchmark:
<<<<<<< Updated upstream
        runner = BenchmarkRunner(config.benchmark)
        results = runner.run_suite()
        reporter.report(results)  
=======
        results = runner.run_suite()
        reporter.report(results)

>>>>>>> Stashed changes

if __name__ == '__main__':
    main()