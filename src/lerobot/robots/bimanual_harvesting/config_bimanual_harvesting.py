"""Native LeRobot configuration for the harvesting hardware."""

from dataclasses import dataclass, field

from lerobot.cameras import CameraConfig
from lerobot.robots.config import RobotConfig
from lerobot.robots.so_follower.config_so_follower import SOFollowerConfig
from lerobot.robots.twister.config_twister import TwisterHardwareConfig


@RobotConfig.register_subclass("bimanual_harvesting")
@dataclass
class BimanualHarvestingConfig(RobotConfig):
    # Match the native BiSOFollower CLI: left is Twister, right is SO100.
    left_arm_config: TwisterHardwareConfig
    right_arm_config: SOFollowerConfig
    cameras: dict[str, CameraConfig] = field(default_factory=dict)

    def __post_init__(self) -> None:
        RobotConfig.__post_init__(self)
        self.left_arm_config.validate()
        if self.left_arm_config.port.casefold() == self.right_arm_config.port.casefold():
            raise ValueError("Twister and SO100 require separate controller serial ports.")
        if not self.right_arm_config.use_degrees:
            raise ValueError("bimanual_harvesting uses arm joint degrees; set right_arm_config.use_degrees=true.")
