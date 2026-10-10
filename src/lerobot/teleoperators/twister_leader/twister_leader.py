"""Passive matching two-servo leader for normal LeRobot teleoperation."""

from lerobot.teleoperators.teleoperator import Teleoperator
from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected

from lerobot.teleoperators.twister_leader.config_twister_leader import TwisterLeaderConfig
from lerobot.robots.twister.control import JOINT_FEATURES
from lerobot.robots.twister.device import TwisterDeviceMixin


class TwisterLeader(TwisterDeviceMixin, Teleoperator):
    config_class = TwisterLeaderConfig
    name = "twister_leader"

    def __init__(self, config: TwisterLeaderConfig):
        super().__init__(config)
        self.config = config
        self._init_device()

    @property
    def action_features(self) -> dict:
        return dict(JOINT_FEATURES)

    @property
    def feedback_features(self) -> dict:
        return dict(JOINT_FEATURES)

    @property
    def is_connected(self) -> bool:
        return self.bus.is_connected

    @check_if_already_connected
    def connect(self, calibrate: bool = True) -> None:
        try:
            self._connect_bus(calibrate)
        except BaseException:
            try:
                self._disconnect_resources()
            except Exception:
                pass
            raise

    @check_if_not_connected
    def get_action(self) -> dict[str, float]:
        return self._read_positions()

    @check_if_not_connected
    def send_feedback(self, feedback: dict[str, float]) -> None:
        self._write_prepared(self.prepare_action(feedback))

    @check_if_not_connected
    def enable_torque(self) -> None:
        self._seed_hold_position()
        with self._bus_lock:
            self.bus.enable_torque()
        if self._rotation_loop is not None:
            self._rotation_loop.set_enabled(True)

    @check_if_not_connected
    def disable_torque(self) -> None:
        if self._rotation_loop is not None:
            self._rotation_loop.set_enabled(False)
        with self._bus_lock:
            self.bus.disable_torque()

    def disconnect(self) -> None:
        self._disconnect_resources()
