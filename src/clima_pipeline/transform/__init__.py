# Mesmo atalho de import usado em extract/__init__.py e load/__init__.py.
from clima_pipeline.transform.aggregator import ClimaAggregator
from clima_pipeline.transform.cleaner import ClimaCleaner

__all__ = ["ClimaCleaner", "ClimaAggregator"]
