"""Native LeRobot configuration for the harvesting hardware."""

from dataclasses import dataclass, field
from typing import Literal

from lerobot.cameras import CameraConfig
from lerobot.robots.config import RobotConfig

from .control import DEGREES_PER_TICK, MAX_ROTATION_DEG, UnwrappedEncoder, finite_number


@dataclass
class TwisterHardwareConfig:
    port: str
    rotation_motor_id: int = 1
    gripper_motor_id: int = 2
    # Select the encoder seam at calibration time; never reset this at startup.
    rotation_homing_offset: int = 0
    gripper_inverted: bool = False
    # Direct-drive shaft; degrees are cumulative from the connection starting pose.
    rotation_control: Literal["continuous", "single_turn"] = "continuous"
    rotation_min_deg: float = -720.0
    rotation_max_deg: float = 720.0
    control_hz: float = 50.0
    max_tracking_gap_s: float = 0.15
    max_tracking_speed_deg_s: float = 720.0
    rotation_kp: float = 2.0
    rotation_tolerance_deg: float = 0.5
    command_timeout_s: float = 1.0
    rotation_velocity_sign: int = 1
    # This option applies only to the optional bounded single_turn mode.
    stop_on_encoder_wrap: bool = True
    max_relative_target: float | dict[str, float] | None = None
    # Speed cap in continuous mode; position-profile speed in single_turn mode.
    rotation_speed: int = 400
    gripper_speed: int = 400
    acceleration: int = 20
    rotation_torque_limit: int = 500
    gripper_torque_limit: int = 250
    protection_current: int = 250
    position_p_coefficient: int = 16
    position_i_coefficient: int = 0
    position_d_coefficient: int = 32
    num_read_retries: int = 2
    disable_torque_on_disconnect: bool = True
    cameras: dict[str, CameraConfig] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.port:
            raise ValueError("A serial port is required.")
        for value in [self.rotation_motor_id, self.gripper_motor_id]:
            if type(value) is not int or not 1 <= value <= 253:
                raise ValueError("Motor IDs must be integers in 1..253.")
        if self.rotation_motor_id == self.gripper_motor_id:
            raise ValueError("Rotation and gripper motor IDs must differ on their shared bus.")
        if type(self.rotation_homing_offset) is not int or abs(self.rotation_homing_offset) > 2047:
            raise ValueError("rotation_homing_offset must be an integer in -2047..2047.")
        low = finite_number(self.rotation_min_deg, "rotation_min_deg")
        high = finite_number(self.rotation_max_deg, "rotation_max_deg")
        if self.rotation_control not in ("continuous", "single_turn"):
            raise ValueError("rotation_control must be continuous or single_turn.")
        if self.rotation_control == "single_turn":
            if not 0 <= low < high <= MAX_ROTATION_DEG:
                raise ValueError(f"Single-turn limits must satisfy 0 <= min < max <= {MAX_ROTATION_DEG}.")
        elif not low < 0 < high:
            raise ValueError("Continuous rotation limits must enclose the session starting position, zero.")
        for name in ["control_hz", "max_tracking_gap_s", "max_tracking_speed_deg_s", "rotation_kp",
                     "rotation_tolerance_deg", "command_timeout_s"]:
            if finite_number(getattr(self, name), name) <= 0:
                raise ValueError(f"{name} must be positive.")
        if not 10 <= self.control_hz <= 200 or 2 / self.control_hz >= self.max_tracking_gap_s:
            raise ValueError("control_hz must be 10..200 with at least two sample periods inside the gap limit.")
        UnwrappedEncoder(self.max_tracking_gap_s, self.max_tracking_speed_deg_s)
        if type(self.rotation_velocity_sign) is not int or self.rotation_velocity_sign not in (-1, 1):
            raise ValueError("rotation_velocity_sign must be +1 or -1.")
        limits = self.max_relative_target
        if isinstance(limits, dict):
            if set(limits) != {"rotation", "gripper"}:
                raise ValueError("max_relative_target must contain rotation and gripper (without .pos).")
            caps = list(limits.values())
        else:
            caps = [] if limits is None else [limits]
        if any(finite_number(value, "max_relative_target") <= 0 for value in caps):
            raise ValueError("Relative target limits must be positive.")
        for name, maximum in [
            ("rotation_speed", 32767), ("gripper_speed", 32767), ("acceleration", 254),
            ("rotation_torque_limit", 1000), ("gripper_torque_limit", 1000),
            ("protection_current", 1023),
        ]:
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError(f"{name} must be an integer in 1..{maximum}.")
        if self.rotation_control == "continuous" and self.rotation_speed * DEGREES_PER_TICK > self.max_tracking_speed_deg_s:
            raise ValueError("rotation_speed exceeds the encoder tracking speed limit.")
        for name in ["position_p_coefficient", "position_i_coefficient", "position_d_coefficient"]:
            if type(getattr(self, name)) is not int or not 0 <= getattr(self, name) <= 254:
                raise ValueError(f"{name} must be an integer in 0..254.")
        if type(self.num_read_retries) is not int or self.num_read_retries < 0:
            raise ValueError("num_read_retries must be a nonnegative integer.")


@RobotConfig.register_subclass("twister")
@dataclass
class TwisterConfig(RobotConfig, TwisterHardwareConfig):
    def __post_init__(self) -> None:
        RobotConfig.__post_init__(self)
        self.validate()
