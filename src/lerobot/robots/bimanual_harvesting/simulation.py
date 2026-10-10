"""Dependency-free joint contract for a future LeIsaac adapter (not an Isaac environment)."""

import math
from collections.abc import Mapping

from lerobot.robots.twister.control import finite_number

TWISTER_ORDER = ("rotation.pos", "gripper.pos")
HARVESTING_ORDER = (
    "twister_rotation.pos", "twister_gripper.pos", "arm_shoulder_pan.pos", "arm_shoulder_lift.pos",
    "arm_elbow_flex.pos", "arm_wrist_flex.pos", "arm_wrist_roll.pos", "arm_gripper.pos",
)


def angle_to_sim_radians(
    degrees: float, *, start_radians: float = 0.0, direction: int = 1
) -> float:
    """Direct-drive cumulative session degrees -> simulated joint radians."""
    if direction not in (-1, 1) or isinstance(direction, bool):
        raise ValueError("direction must be +1 or -1.")
    return finite_number(start_radians, "start_radians") + direction * math.radians(finite_number(degrees, "degrees"))


def sim_radians_to_angle(
    radians: float, *, start_radians: float = 0.0, direction: int = 1
) -> float:
    # Reuse input validation; do not modulo angles or hide out-of-window simulation states.
    angle_to_sim_radians(0, start_radians=start_radians, direction=direction)
    return direction * math.degrees(finite_number(radians, "radians") - finite_number(start_radians, "start_radians"))


def gripper_to_sim_radians(percent: float, *, at_zero_radians: float, at_hundred_radians: float) -> float:
    value = finite_number(percent, "gripper percent")
    if not 0 <= value <= 100:
        raise ValueError("Gripper percent must be in 0..100.")
    zero = finite_number(at_zero_radians, "gripper zero")
    hundred = finite_number(at_hundred_radians, "gripper hundred")
    if zero == hundred:
        raise ValueError("Simulated gripper endpoints must differ.")
    return zero + value * (hundred - zero) / 100


def ordered_vector(values: Mapping[str, float], order: tuple[str, ...]) -> list[float]:
    if set(values) != set(order):
        raise ValueError("Simulation vector features must exactly match the hardware contract.")
    return [finite_number(values[key], key) for key in order]
