# infrastructure/hardware/collectors/power.py

import logging

logger = logging.getLogger(__name__)

# get_hardware_info создать класс в entities/hardware может ли собираться мощность цпу и гпу (bool)

# get_metrics возвращает datapoint (entities/metrics) насколько загружены гпу и цпу

class PWRCollector(BaseCollector): # TODO this
    ...