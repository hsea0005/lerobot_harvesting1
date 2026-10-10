"""Direct-drive angle conversions and continuous tracking, independent of ML dependencies."""

import math
from collections.abc import Mapping
from typing import Any

RESOLUTION = 4096
DEGREES_PER_TICK = 360.0 / RESOLUTION
MAX_ROTATION_DEG = (RESOLUTION - 1) * DEGREES_PER_TICK
JOINT_FEATURES = {"rotation.pos": float, "gripper.pos": float}


class EncoderBoundaryError(RuntimeError):
    """A latched single-turn encoder discontinuity; reconnect after repositioning."""


class RotationTrackingError(RuntimeError):
    """Turn count cannot be trusted; stop and reconnect to establish a new reference."""


class UnwrappedEncoder:
    """Accumulate signed displacement relative to the first observed raw angle.

    A 359 -> 1 degree reading adds +2 degrees. This requires timely samples and a
    movement bound below half a revolution between samples, not a persistent turn encoder.
    """

    def __init__(self, max_gap_s: float = 0.15, max_speed_deg_s: float = 720.0):
        self.max_gap_s = finite_number(max_gap_s, "max_gap_s")
        self.max_speed_deg_s = finite_number(max_speed_deg_s, "max_speed_deg_s")
        if self.max_gap_s <= 0 or self.max_speed_deg_s <= 0:
            raise ValueError("Tracking gap and speed limits must be positive.")
        if self.max_gap_s * self.max_speed_deg_s + 2.0 >= 180:
            raise ValueError("Tracking bounds must exclude a half turn between samples.")
        self.previous_ticks: float | None = None
        self.timestamp: float | None = None
        self.total_ticks = 0.0
        self.fault: str | None = None

    def update(self, raw_ticks: int | float, now: float) -> float:
        if self.fault:
            raise RotationTrackingError(self.fault)
        try:
            ticks_to_degrees(raw_ticks)
            ticks = float(raw_ticks)
            stamp = finite_number(now, "sample timestamp")
            if self.previous_ticks is None:
                self.previous_ticks, self.timestamp = ticks, stamp
                return 0.0
            elapsed = stamp - self.timestamp
            if elapsed <= 0 or elapsed > self.max_gap_s:
                raise RotationTrackingError("Encoder samples were delayed; cumulative turn count is ambiguous.")
            delta = ((ticks - self.previous_ticks + RESOLUTION / 2) % RESOLUTION) - RESOLUTION / 2
            delta_deg = abs(delta * DEGREES_PER_TICK)
            if delta_deg > self.max_speed_deg_s * elapsed + 2.0:
                raise RotationTrackingError("Encoder displacement exceeds the configured tracking speed bound.")
            self.total_ticks += delta
            self.previous_ticks, self.timestamp = ticks, stamp
            return self.total_ticks * DEGREES_PER_TICK
        except (ValueError, EncoderBoundaryError, RotationTrackingError) as exc:
            self.fault = str(exc)
            raise RotationTrackingError(self.fault) from exc


class PositionVelocityController:
    """Absolute cumulative position target -> bounded signed Feetech speed command."""

    def __init__(self, kp: float, max_speed_ticks_s: int, tolerance_deg: float,
                 command_timeout_s: float, direction: int = 1):
        self.kp = finite_number(kp, "rotation_kp")
        self.max_speed = max_speed_ticks_s
        self.tolerance = finite_number(tolerance_deg, "rotation_tolerance_deg")
        self.timeout = finite_number(command_timeout_s, "command_timeout_s")
        if self.kp <= 0 or self.max_speed <= 0 or self.tolerance <= 0 or self.timeout <= 0:
            raise ValueError("Controller settings must be positive.")
        if direction not in (-1, 1) or isinstance(direction, bool):
            raise ValueError("rotation_velocity_sign must be +1 or -1.")
        self.direction = direction
        self.target = 0.0
        self.last_command: float | None = None

    def set_target(self, target_deg: float, now: float) -> None:
        self.target = finite_number(target_deg, "rotation.pos")
        self.last_command = finite_number(now, "command timestamp")

    def velocity(self, position_deg: float, now: float, enabled: bool = True) -> int:
        if not enabled or self.last_command is None or now - self.last_command > self.timeout:
            return 0
        error_deg = self.target - position_deg
        if abs(error_deg) <= self.tolerance:
            return 0
        ticks_s = self.kp * error_deg / DEGREES_PER_TICK
        return self.direction * round(min(self.max_speed, max(-self.max_speed, ticks_s)))


class BoundaryGuard:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.previous: float | None = None
        self.faulted = False

    def reset(self) -> None:
        self.previous = None
        self.faulted = False

    def check(self, angle: float) -> float:
        if self.faulted:
            raise EncoderBoundaryError("Encoder boundary fault is latched. Reposition and reconnect.")
        if self.enabled and self.previous is not None and abs(angle - self.previous) > 180.0:
            self.faulted = True
            raise EncoderBoundaryError(
                f"Single-turn encoder boundary crossed ({self.previous:.2f} -> {angle:.2f} degrees). "
                "The selected single_turn mode cannot follow cumulative rotation. "
                "Move back into the working window and restart."
            )
        self.previous = angle
        return angle


def finite_number(value: Any, name: str) -> float:
    if isinstance(value, (bool, str, bytes)):
        raise ValueError(f"{name} must be a finite number.")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number.") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number.")
    return result


def validate_action(action: Mapping[str, Any], features: Mapping[str, Any]) -> dict[str, float]:
    if set(action) != set(features):
        raise ValueError(
            f"Action keys must match the robot. Missing: {sorted(set(features) - set(action))}; "
            f"unexpected: {sorted(set(action) - set(features))}."
        )
    return {key: finite_number(action[key], key) for key in features}


def ticks_to_degrees(ticks: int | float) -> float:
    value = finite_number(ticks, "rotation encoder")
    if not 0 <= value <= RESOLUTION - 1:
        raise EncoderBoundaryError(f"Rotation encoder is outside 0..4095: {value}.")
    return value * DEGREES_PER_TICK


def degrees_to_ticks(degrees: float) -> int:
    angle = finite_number(degrees, "rotation.pos")
    if not 0 <= angle <= MAX_ROTATION_DEG:
        raise ValueError(f"rotation.pos must be within 0..{MAX_ROTATION_DEG:.6f} degrees; got {angle}.")
    return min(RESOLUTION - 1, round(angle / DEGREES_PER_TICK))


def ticks_to_gripper(ticks: int | float, low: int, high: int, inverted: bool = False) -> float:
    if high <= low:
        raise ValueError("Gripper calibration must have a positive range.")
    value = min(high, max(low, ticks))
    percent = (value - low) * 100.0 / (high - low)
    return 100.0 - percent if inverted else percent


def gripper_to_ticks(percent: float, low: int, high: int, inverted: bool = False) -> int:
    if high <= low:
        raise ValueError("Gripper calibration must have a positive range.")
    value = min(100.0, max(0.0, finite_number(percent, "gripper.pos")))
    if inverted:
        value = 100.0 - value
    # Match LeRobot's RANGE_0_100 integer conversion.
    return int(low + value * (high - low) / 100.0)


def clamp_relative(goal: float, present: float, cap: float | None) -> float:
    if cap is None:
        return goal
    return present + min(cap, max(-cap, goal - present))
