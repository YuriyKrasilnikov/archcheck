"""Discovery layer for architecture analysis.

Functions to discover project structure:
- Layers from directory structure
- Modules from .py files
- Known libraries from requirements files
"""

from archcheck.application.discovery.layers import discover_layers
from archcheck.application.discovery.libs import load_known_libs
from archcheck.application.discovery.modules import discover_modules

__all__ = [
    "discover_layers",
    "discover_modules",
    "load_known_libs",
]
