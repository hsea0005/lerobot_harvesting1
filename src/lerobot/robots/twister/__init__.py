"""Native Twister hardware support."""

from typing import TYPE_CHECKING

from .config_twister import TwisterConfig, TwisterHardwareConfig

if TYPE_CHECKING:
    from .twister import Twister

__all__ = ['Twister', 'TwisterConfig', 'TwisterHardwareConfig']

def __getattr__(name: str):
    if name == "Twister":
        from .twister import Twister

        return Twister
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
