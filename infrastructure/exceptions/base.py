# infrastructure/exceptions/base.py

class RaBenchmarkException(Exception):
    """Базовое исключение для всех ошибок бенчмарка."""
    pass


class ConfigError(RaBenchmarkException):
    """Ошибка конфигурации бенчмарка."""
    pass


class DatasetError(RaBenchmarkException):
    """Ошибка работы с датасетом."""
    pass


class ModelError(RaBenchmarkException):
    """Базовое исключение для ошибок работы с моделями."""
    pass