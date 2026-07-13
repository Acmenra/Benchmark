# infrastructure/hardware/collectors/ram.py

# контракт - BaseCollector (infrastructure\hardware\collectors\base.py)

# get_hardware_info пока сделать raise not implemented
# get_metrics возвращает сколько загружено памяти (ram_usage: MetricStatistics) В ENTITY/METRICS

# TODO думать, что делать если у нас RAM и что делать если Unified memory (к кому относить)

class RAMCollector(BaseCollector): # TODO this
    ...