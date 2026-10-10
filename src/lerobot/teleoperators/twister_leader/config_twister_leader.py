"""Native LeRobot configuration for the harvesting hardware."""

from dataclasses import dataclass

from lerobot.robots.twister.config_twister import TwisterHardwareConfig
from lerobot.teleoperators.config import TeleoperatorConfig


@TeleoperatorConfig.register_subclass("twister_leader")
@dataclass
class TwisterLeaderConfig(TeleoperatorConfig, TwisterHardwareConfig):
    def __post_init__(self) -> None:
        self.validate()
        if self.cameras:
            raise ValueError("Configure cameras on the follower robot, not the leader.")
