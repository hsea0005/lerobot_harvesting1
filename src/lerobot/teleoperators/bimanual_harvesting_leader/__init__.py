"""Native BimanualHarvestingLeader hardware support."""

from typing import TYPE_CHECKING

from .config_bimanual_harvesting_leader import BimanualHarvestingLeaderConfig

if TYPE_CHECKING:
    from .bimanual_harvesting_leader import BimanualHarvestingLeader

__all__ = ['BimanualHarvestingLeader', 'BimanualHarvestingLeaderConfig']

def __getattr__(name: str):
    if name == "BimanualHarvestingLeader":
        from .bimanual_harvesting_leader import BimanualHarvestingLeader

        return BimanualHarvestingLeader
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
