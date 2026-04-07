"""Analytics method registry and base class."""

from abc import ABC, abstractmethod
from typing import Dict, Any

from models.stock import StockData


class AnalyticsMethod(ABC):
    """Base class for all analytics methods."""

    @abstractmethod
    def run(self, data: StockData) -> Dict[str, Any]:
        ...


class _Registry:
    def __init__(self):
        self._methods: Dict[str, AnalyticsMethod] = {}

    def register(self, name: str):
        """Decorator to register an analytics method by name."""
        def decorator(cls):
            self._methods[name] = cls()
            return cls
        return decorator

    def get(self, name: str) -> AnalyticsMethod:
        return self._methods[name]

    def get_all(self) -> Dict[str, AnalyticsMethod]:
        return dict(self._methods)

    def names(self):
        return list(self._methods.keys())


registry = _Registry()
