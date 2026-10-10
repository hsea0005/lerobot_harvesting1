"""LeRobot physical two-joint follower robot."""

from typing import Any

from lerobot.cameras import DepthCamera, make_cameras_from_configs
from lerobot.robots.robot import Robot
from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected

from lerobot.robots.twister.config_twister import TwisterConfig
from .control import JOINT_FEATURES
from .device import TwisterDeviceMixin


class Twister(TwisterDeviceMixin, Robot):
    config_class = TwisterConfig
    name = "twister"
    is_follower = True

    def __init__(self, config: TwisterConfig):
        super().__init__(config)
        self.config = config
        self._init_device()
        self.cameras = make_cameras_from_configs(config.cameras)
        if set(self._camera_features) & set(JOINT_FEATURES):
            raise ValueError("Camera names must not collide with joint features.")

    @property
    def _camera_features(self) -> dict[str, tuple[int, int, int]]:
        features = {}
        for key, camera in self.cameras.items():
            if getattr(camera, "use_rgb", True):
                features[key] = (camera.height, camera.width, 3)
            if isinstance(camera, DepthCamera) and camera.use_depth:
                features[f"{key}_depth"] = (camera.height, camera.width, 1)
        return features

    @property
    def observation_features(self) -> dict:
        return {**JOINT_FEATURES, **self._camera_features}

    @property
    def action_features(self) -> dict:
        return dict(JOINT_FEATURES)

    @property
    def is_connected(self) -> bool:
        return self.bus.is_connected and all(camera.is_connected for camera in self.cameras.values())

    @check_if_already_connected
    def connect(self, calibrate: bool = True) -> None:
        try:
            self._connect_bus(calibrate)
            for camera in self.cameras.values():
                camera.connect()
        except BaseException:
            try:
                self._disconnect_resources()
            except Exception:
                pass  # Preserve the original connect failure.
            raise

    @check_if_not_connected
    def get_observation(self) -> dict[str, Any]:
        observation: dict[str, Any] = self._read_positions()
        for key, camera in self.cameras.items():
            if getattr(camera, "use_rgb", True):
                observation[key] = camera.read_latest()
            if isinstance(camera, DepthCamera) and camera.use_depth:
                observation[f"{key}_depth"] = camera.read_latest_depth()
        return observation

    @check_if_not_connected
    def send_action(self, action: dict[str, Any]) -> dict[str, float]:
        return self._write_prepared(self.prepare_action(action))

    def disconnect(self) -> None:
        self._disconnect_resources()
