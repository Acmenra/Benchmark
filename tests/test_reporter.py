# tests/test_reporter.py

import logging

from core.entities.metrics import DataPoint, MetricStatistics
from infrastructure.reporting.utils import to_plain_data

logger = logging.getLogger(__name__)


def test_metric_statistics_serializes_as_summary() -> None:
    metric = MetricStatistics(unit="percent")
    metric.history.extend(
        [
            DataPoint(time_in_ms=1, value=10.0),
            DataPoint(time_in_ms=2, value=20.0),
            DataPoint(time_in_ms=3, value=30.0),
        ]
    )

    result = to_plain_data(metric)

    assert result == {
        "unit": "percent",
        "samples": 3,
        "mean": 20.0,
        "p50": 20.0,
        "p95": 20.0,
        "p99": 20.0,
        "min": 10.0,
        "max": 30.0,
    }
