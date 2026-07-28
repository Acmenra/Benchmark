import logging
from application.benchmark.runner import BenchmarkRunner
from application.cli import parse_config_path
from core.domain.config import SystemInfoConfig
from infrastructure.config.default_config import build_default_config
from infrastructure.config.config_reader import read_yaml
from application.benchmark.reporter import Reporter
from infrastructure.hardware.collectors.base import BaseHardwareCollector
from infrastructure.reporting import CSVReporter, JSONReporter
from infrastructure.hardware.collector import HardwareCollector


logger = logging.getLogger(__name__)


def print_system_banner(system_info) -> None:
    """Выводит красивую информацию о системе при старте бенчмарка."""

    # ASCII art заголовок
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                         EDGE AI BENCHMARK SUITE                              ║
║                              System Information                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)

    # Информация о платформе
    print(f"🖥️  Platform: {system_info.platform.value if system_info.platform else 'Unknown'}")
    print(f"📛 Device:   {system_info.device_name or 'Not specified'}")
    print()

    # CPU информация
    if system_info.cpu:
        print("┌─ CPU ─────────────────────────────────────────────────────────────────────┐")
        print(f"│ Name:         {system_info.cpu.name or 'Unknown'}")
        print(f"│ Architecture: {system_info.cpu.architecture or 'Unknown'}")
        print(
            f"│ Cores:        {system_info.cpu.physical_cores or '?'} physical, {system_info.cpu.logical_cores or '?'} logical")
        if system_info.cpu.max_frequency_mhz:
            print(f"│ Max Freq:     {system_info.cpu.max_frequency_mhz:.0f} MHz")
        print("└───────────────────────────────────────────────────────────────────────────┘")
        print()

    # RAM информация
    if system_info.ram:
        print("┌─ RAM ───────────────────────────────────────────────────────────────────────┐")
        if system_info.ram.total_mb:
            total_gb = system_info.ram.total_mb / 1024
            print(f"│ Total:        {total_gb:.1f} GB ({system_info.ram.total_mb} MB)")
        if system_info.ram.type:
            print(f"│ Type:         {system_info.ram.type}")
        print("└───────────────────────────────────────────────────────────────────────────┘")
        print()


    # GPU информация
    if system_info.gpu:
        print("┌─ GPU ─────────────────────────────────────────────────────────────────────┐")
        print(f"│ Name:         {system_info.gpu.name or 'Unknown'}")
        if system_info.gpu.memory_mb:
            print(f"│ Memory:       {system_info.gpu.memory_mb} MB")
        if system_info.gpu.driver_version:
            print(f"│ Driver:       {system_info.gpu.driver_version}")
        if system_info.gpu.cuda_version:
            print(f"│ CUDA:         {system_info.gpu.cuda_version}")
        elif system_info.gpu.name and "Apple" in system_info.gpu.name:
            print(f"│ Backend:      Metal Performance Shaders (MPS)")
        print("└───────────────────────────────────────────────────────────────────────────┘")
        print()

    # OS информация
    if system_info.os:
        print("┌─ Operating System ────────────────────────────────────────────────────────┐")
        print(f"│ System:       {system_info.os.system or 'Unknown'}")
        print(f"│ Release:      {system_info.os.release or 'Unknown'}")
        print(f"│ Kernel:       {system_info.os.kernel or 'Unknown'}")
        print(f"│ Architecture: {system_info.os.architecture or 'Unknown'}")
        print("└───────────────────────────────────────────────────────────────────────────┘")
        print()

    # Temperature capabilities
    if system_info.temperature:
        print("┌─ Temperature Sensors ─────────────────────────────────────────────────────┐")
        cpu_temp = "✅ Available" if system_info.temperature.cpu_sensor_available else "❌ Not available"
        gpu_temp = "✅ Available" if system_info.temperature.gpu_sensor_available else "❌ Not available"
        print(f"│ CPU Sensor:   {cpu_temp}")
        print(f"│ GPU Sensor:   {gpu_temp}")
        print("└───────────────────────────────────────────────────────────────────────────┘")
        print()

    print("=" * 80)
    print()


def main() -> None:
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    config_path = parse_config_path()
    config = build_default_config() if config_path is None else read_yaml(config_path)

    if config.system_info:
        collector = HardwareCollector(config.system_info)
        system_info = collector.get_system_info()

        print_system_banner(system_info)

    output_config = config.output
    reporters = {}
    if "csv" in output_config.formats:
        reporters["csv"] = CSVReporter(output_config.directory)
    if "json" in output_config.formats:
        reporters["json"] = JSONReporter(output_config.directory)

    enabled_formats = [f for f in output_config.formats if f in reporters]
    reporter = Reporter(reporters, enabled_formats)

    # Сохраняем информацию о системе в отчет
    if config.system_info and system_info:
        reporter.report(system_info)

    quit()
    # Запуск бенчмарка
    if config.benchmark:
        runner = BenchmarkRunner(benchmark_config=config.benchmark,
                                 system_info_config=config.system_info)
        for result in runner.run_suite():
            reporter.report(result)


if __name__ == '__main__':
    main()