"""One matching Twister leader plus one normal SO100 leader."""

from lerobot.teleoperators.so_leader import SOLeader, SOLeaderTeleopConfig
from lerobot.teleoperators.teleoperator import Teleoperator
from lerobot.utils.decorators import check_if_not_connected

from lerobot.teleoperators.bimanual_harvesting_leader.config_bimanual_harvesting_leader import BimanualHarvestingLeaderConfig
from lerobot.teleoperators.twister_leader.config_twister_leader import TwisterLeaderConfig
from lerobot.robots.twister.control import validate_action
from lerobot.robots.bimanual_harvesting.pair import HarvestingPairMixin, prefixed, split
from lerobot.teleoperators.twister_leader.twister_leader import TwisterLeader


class BimanualHarvestingLeader(HarvestingPairMixin, Teleoperator):
    config_class = BimanualHarvestingLeaderConfig
    name = "bimanual_harvesting_leader"

    def __init__(self, config: BimanualHarvestingLeaderConfig):
        super().__init__(config)
        self.config = config
        self.twister = TwisterLeader(TwisterLeaderConfig(
            id=f"{config.id}_twister" if config.id else None,
            calibration_dir=config.calibration_dir, **vars(config.left_arm_config),
        ))
        self.arm = SOLeader(SOLeaderTeleopConfig(
            id=f"{config.id}_arm" if config.id else None,
            calibration_dir=config.calibration_dir, **vars(config.right_arm_config),
        ))
        self.left_arm, self.right_arm = self.twister, self.arm

    @property
    def action_features(self) -> dict:
        return {**prefixed(self.twister.action_features, "twister"), **prefixed(self.arm.action_features, "arm")}

    @property
    def feedback_features(self) -> dict:
        return self.action_features

    @check_if_not_connected
    def get_action(self) -> dict[str, float]:
        return {**prefixed(self.twister.get_action(), "twister"), **prefixed(self.arm.get_action(), "arm")}

    @check_if_not_connected
    def send_feedback(self, feedback: dict[str, float]) -> None:
        values = validate_action(feedback, self.feedback_features)
        prepared = self.twister.prepare_action(split(values, "twister"))
        self.twister._write_prepared(prepared)
        self.arm.send_feedback(split(values, "arm"))

    @check_if_not_connected
    def enable_torque(self) -> None:
        self.twister.enable_torque()
        self.arm.enable_torque()

    @check_if_not_connected
    def disable_torque(self) -> None:
        self.twister.disable_torque()
        self.arm.disable_torque()
