"""Registry loader for canonical chart functions in fantasy-data."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml


@dataclass
class CanonicalChart:
    name: str
    description: str
    function: Callable[..., Any]
    parameters: dict[str, dict]


def load_registry(path: str | Path) -> dict[str, CanonicalChart]:
    """Load the chart registry YAML and resolve each function to a callable.

    Raises immediately if a function path can't be imported — a broken
    registry is a configuration bug, not something to swallow at runtime.
    """
    with open(path) as f:
        raw = yaml.safe_load(f)

    charts = raw.get("charts") or {}
    registry: dict[str, CanonicalChart] = {}

    for name, entry in charts.items():
        module_path, func_name = entry["function"].split(":")
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)
        registry[name] = CanonicalChart(
            name=name,
            description=entry["description"],
            function=func,
            parameters=entry.get("parameters", {}),
        )

    return registry
