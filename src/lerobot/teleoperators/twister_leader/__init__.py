"""Native TwisterLeader hardware support."""

from typing import TYPE_CHECKING

from .config_twister_leader import TwisterLeaderConfig

if TYPE_CHECKING:
    from .twister_leader import TwisterLeader

__all__ = ['TwisterLeader', 'TwisterLeaderConfig']

def __getattr__(name: str):
    if name == "TwisterLeader":
        from .twister_leader import TwisterLeader

        return TwisterLeader
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
