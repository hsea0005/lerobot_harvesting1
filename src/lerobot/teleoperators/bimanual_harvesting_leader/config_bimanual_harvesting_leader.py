"""Native LeRobot configuration for the harvesting hardware."""

from dataclasses import dataclass

from lerobot.robots.twister.config_twister import TwisterHardwareConfig
from lerobot.teleoperators.config import TeleoperatorConfig
from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderConfig


@TeleoperatorConfig.register_subclass("bimanual_harvesting_leader")
@dataclass
class BimanualHarvestingLeaderConfig(TeleoperatorConfig):
    left_arm_config: TwisterHardwareConfig
    right_arm_config: SOLeaderConfig

    def __post_init__(self) -> None:
        self.left_arm_config.validate()
        if self.left_arm_config.cameras:
            raise ValueError("Configure cameras on the follower robot, not the leader.")
        if self.left_arm_config.port.casefold() == self.right_arm_config.port.casefold():
            raise ValueError("Twister and SO100 leaders require separate serial ports.")
        if not self.right_arm_config.use_degrees:
            raise ValueError("bimanual_harvesting uses arm joint degrees; set right_arm_config.use_degrees=true.")
