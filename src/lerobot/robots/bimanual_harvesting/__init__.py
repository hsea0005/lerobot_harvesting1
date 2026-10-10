"""Native BimanualHarvesting hardware support."""

from typing import TYPE_CHECKING

from .config_bimanual_harvesting import BimanualHarvestingConfig

if TYPE_CHECKING:
    from .bimanual_harvesting import BimanualHarvesting

__all__ = ['BimanualHarvesting', 'BimanualHarvestingConfig']

def __getattr__(name: str):
    if name == "BimanualHarvesting":
        from .bimanual_harvesting import BimanualHarvesting

        return BimanualHarvesting
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
