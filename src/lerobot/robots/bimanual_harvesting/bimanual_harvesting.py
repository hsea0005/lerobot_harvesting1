"""One Twister follower plus one standard SO100, exposed as a single Robot."""

from typing import Any

from lerobot.cameras import DepthCamera, make_cameras_from_configs
from lerobot.robots.robot import Robot
from lerobot.robots.so_follower import SOFollower, SOFollowerRobotConfig
from lerobot.utils.decorators import check_if_not_connected

from lerobot.robots.bimanual_harvesting.config_bimanual_harvesting import BimanualHarvestingConfig
from lerobot.robots.twister.config_twister import TwisterConfig
from lerobot.robots.twister.control import validate_action
from .pair import HarvestingPairMixin, prefixed, split
from lerobot.robots.twister.twister import Twister


class BimanualHarvesting(HarvestingPairMixin, Robot):
    config_class = BimanualHarvestingConfig
    name = "bimanual_harvesting"

    def __init__(self, config: BimanualHarvestingConfig):
        super().__init__(config)
        self.config = config
        twister_config = TwisterConfig(
            id=f"{config.id}_twister" if config.id else None,
            calibration_dir=config.calibration_dir, **vars(config.left_arm_config),
        )
        arm_config = SOFollowerRobotConfig(
            id=f"{config.id}_arm" if config.id else None,
            calibration_dir=config.calibration_dir, **vars(config.right_arm_config),
        )
        self.twister = Twister(twister_config)
        self.arm = SOFollower(arm_config)
        self.left_arm, self.right_arm = self.twister, self.arm
        self._scene_cameras = make_cameras_from_configs(config.cameras)
        self.cameras = {
            **prefixed(self.twister.cameras, "twister"),
            **prefixed(self.arm.cameras, "arm"), **self._scene_cameras,
        }
        camera_keys = set(self._scene_camera_features)
        child_keys = set(prefixed(self.twister.observation_features, "twister")) | set(
            prefixed(self.arm.observation_features, "arm")
        )
        if camera_keys & child_keys:
            raise ValueError(f"Scene camera names collide with child features: {sorted(camera_keys & child_keys)}")

    @property
    def _scene_camera_features(self) -> dict:
        features = {}
        for key, camera in self._scene_cameras.items():
            if getattr(camera, "use_rgb", True):
                features[key] = (camera.height, camera.width, 3)
            if isinstance(camera, DepthCamera) and camera.use_depth:
                features[f"{key}_depth"] = (camera.height, camera.width, 1)
        return features

    @property
    def action_features(self) -> dict:
        return {**prefixed(self.twister.action_features, "twister"), **prefixed(self.arm.action_features, "arm")}

    @property
    def observation_features(self) -> dict:
        return {
            **prefixed(self.twister.observation_features, "twister"),
            **prefixed(self.arm.observation_features, "arm"), **self._scene_camera_features,
        }

    @check_if_not_connected
    def get_observation(self) -> dict[str, Any]:
        observation = {
            **prefixed(self.twister.get_observation(), "twister"),
            **prefixed(self.arm.get_observation(), "arm"),
        }
        for key, camera in self._scene_cameras.items():
            if getattr(camera, "use_rgb", True):
                observation[key] = camera.read_latest()
            if isinstance(camera, DepthCamera) and camera.use_depth:
                observation[f"{key}_depth"] = camera.read_latest_depth()
        return observation

    @check_if_not_connected
    def send_action(self, action: dict[str, Any]) -> dict[str, float]:
        values = validate_action(action, self.action_features)
        prepared = self.twister.prepare_action(split(values, "twister"))
        # All keys/numbers and the Twister boundary are checked before either device moves.
        twister_sent = self.twister._write_prepared(prepared)
        arm_sent = self.arm.send_action(split(values, "arm"))
        return {**prefixed(twister_sent, "twister"), **prefixed(arm_sent, "arm")}
