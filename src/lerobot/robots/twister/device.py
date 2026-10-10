"""Shared Feetech lifecycle for the two-joint follower and passive leader."""

import logging
import threading
from typing import Any

from lerobot.motors import Motor, MotorCalibration, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus, OperatingMode

from lerobot.robots.twister.config_twister import TwisterHardwareConfig
from .continuous import ContinuousRotationLoop
from .control import (
    BoundaryGuard,
    JOINT_FEATURES,
    clamp_relative,
    degrees_to_ticks,
    gripper_to_ticks,
    ticks_to_degrees,
    ticks_to_gripper,
    validate_action,
)

logger = logging.getLogger(__name__)


class TwisterDeviceMixin:
    """Inherit before Robot/Teleoperator. Their base class owns calibration files."""

    config: TwisterHardwareConfig
    is_follower = False

    def _init_device(self) -> None:
        self.config.validate()
        self.bus = FeetechMotorsBus(
            port=self.config.port,
            motors={
                "rotation": Motor(self.config.rotation_motor_id, "sts3215", MotorNormMode.DEGREES),
                "gripper": Motor(self.config.gripper_motor_id, "sts3215", MotorNormMode.RANGE_0_100),
            },
            calibration=self.calibration,
        )
        self._position_guard = BoundaryGuard(self.config.stop_on_encoder_wrap)
        self._target_guard = BoundaryGuard(self.config.stop_on_encoder_wrap)
        self._bus_lock = threading.RLock()
        self._rotation_loop: ContinuousRotationLoop | None = None

    @property
    def _continuous_rotation(self) -> bool:
        return self.config.rotation_control == "continuous"

    def _stop_rotation_worker(self) -> None:
        if self._rotation_loop is not None:
            loop = self._rotation_loop
            try:
                loop.stop()
            finally:
                # Retain a hung worker so cleanup cannot close a bus it still owns.
                if not loop.is_running:
                    self._rotation_loop = None

    def _validate_calibration(self) -> None:
        if set(self.calibration) != {"rotation", "gripper"}:
            raise ValueError("Calibrate the rotation and gripper joints before use.")
        for name, motor in self.bus.motors.items():
            if self.calibration[name].id != motor.id:
                raise ValueError("Saved calibration uses different motor IDs. Recalibrate with the current IDs.")
        rotation = self.calibration["rotation"]
        if (rotation.range_min, rotation.range_max) != (0, 4095):
            raise ValueError("Rotation calibration must use the full 0..4095 encoder range.")
        if rotation.homing_offset != self.config.rotation_homing_offset:
            raise ValueError("rotation_homing_offset changed. Recalibrate before recording more data.")
        gripper = self.calibration["gripper"]
        if not 0 <= gripper.range_min < gripper.range_max <= 4095:
            raise ValueError("Gripper calibration must stay inside 0..4095 without crossing the seam.")
        if bool(gripper.drive_mode) != self.config.gripper_inverted:
            raise ValueError("gripper_inverted changed. Recalibrate before use.")

    @property
    def is_calibrated(self) -> bool:
        try:
            self._validate_calibration()
        except ValueError:
            return False
        with self._bus_lock:
            return self.bus.is_calibrated

    def calibrate(self) -> None:
        self._stop_rotation_worker()
        if not self.bus.is_connected:
            raise ConnectionError("Connect the motor bus before calibrating.")
        self.bus.disable_torque()
        if self.calibration:
            try:
                self._validate_calibration()
            except ValueError as exc:
                print(f"Existing calibration cannot be reused: {exc}")
            else:
                answer = input(f"ENTER to reuse calibration for {self.id}; 'c' to recalibrate: ")
                if answer.strip().lower() != "c":
                    self.bus.write_calibration(self.calibration)
                    return

        self.bus.configure_motors(acceleration=self.config.acceleration)
        for name in self.bus.motors:
            self.bus.write("Operating_Mode", name, OperatingMode.POSITION.value)
        self.bus.reset_calibration("rotation")
        self.bus.write("Homing_Offset", "rotation", self.config.rotation_homing_offset)
        input("Move ONLY the gripper to the MIDDLE of its safe travel, then press ENTER: ")
        offsets = self.bus.set_half_turn_homings("gripper")
        print("Move ONLY the gripper through its safe endpoints. Do not cross its encoder seam. ENTER ends.")
        lows, highs = self.bus.record_ranges_of_motion(["gripper"])
        self.calibration = {
            "rotation": MotorCalibration(
                id=self.config.rotation_motor_id, drive_mode=0,
                homing_offset=self.config.rotation_homing_offset, range_min=0, range_max=4095,
            ),
            "gripper": MotorCalibration(
                id=self.config.gripper_motor_id, drive_mode=int(self.config.gripper_inverted),
                homing_offset=int(offsets["gripper"]),
                range_min=int(lows["gripper"]), range_max=int(highs["gripper"]),
            ),
        }
        self._validate_calibration()
        self.bus.write_calibration(self.calibration)
        self._save_calibration()
        print(f"Calibration saved to {self.calibration_fpath}. Rotation was not moved to a home pose.")

    def _read_positions(self) -> dict[str, float]:
        self._validate_calibration()
        if self._continuous_rotation:
            if self._rotation_loop is None:
                raise ValueError("Continuous tracking is not running. Finish calibration and reconnect.")
            rotation, raw = self._rotation_loop.snapshot()
        else:
            with self._bus_lock:
                raw = self.bus.sync_read("Present_Position", normalize=False, num_retry=self.config.num_read_retries)
            rotation = self._position_guard.check(ticks_to_degrees(raw["rotation"]))
        cal = self.calibration["gripper"]
        gripper = ticks_to_gripper(raw["gripper"], cal.range_min, cal.range_max, bool(cal.drive_mode))
        return {"rotation.pos": rotation, "gripper.pos": gripper}

    def _seed_hold_position(self) -> None:
        with self._bus_lock:
            raw = self.bus.sync_read("Present_Position", normalize=False, num_retry=self.config.num_read_retries)
            goals = {"gripper": raw["gripper"]} if self._continuous_rotation else raw
            self.bus.sync_write("Goal_Position", goals, normalize=False)
            if self._continuous_rotation:
                self.bus.write("Goal_Velocity", "rotation", 0, normalize=False)

    def configure(self) -> None:
        self._stop_rotation_worker()
        self._validate_calibration()
        self.bus.disable_torque()
        self.bus.configure_motors(acceleration=self.config.acceleration)
        for name in self.bus.motors:
            mode = OperatingMode.VELOCITY if self._continuous_rotation and name == "rotation" else OperatingMode.POSITION
            self.bus.write("Operating_Mode", name, mode.value)
            self.bus.write("P_Coefficient", name, self.config.position_p_coefficient)
            self.bus.write("I_Coefficient", name, self.config.position_i_coefficient)
            self.bus.write("D_Coefficient", name, self.config.position_d_coefficient)
            self.bus.write("Goal_Time", name, 0)
            speed = self.config.rotation_speed if name == "rotation" else self.config.gripper_speed
            if self._continuous_rotation and name == "rotation":
                speed = 0  # Never enable torque with an old nonzero velocity target.
            torque = self.config.rotation_torque_limit if name == "rotation" else self.config.gripper_torque_limit
            self.bus.write("Goal_Velocity", name, speed)
            self.bus.write("Max_Torque_Limit", name, torque)
            self.bus.write("Torque_Limit", name, torque)
            self.bus.write("Protection_Current", name, self.config.protection_current)
            self.bus.write("Overload_Torque", name, 25)
        self._position_guard.reset()
        self._target_guard.reset()
        self._seed_hold_position()
        if self._continuous_rotation:
            self._rotation_loop = ContinuousRotationLoop(
                self.bus, self._bus_lock, self.config, actuate=self.is_follower,
            )
            self._rotation_loop.start()
        else:
            present = self._read_positions()
            self._target_guard.check(present["rotation.pos"])
        if self.is_follower:
            with self._bus_lock:
                self.bus.enable_torque()

    def _connect_bus(self, calibrate: bool) -> None:
        self.bus.connect()
        if not self.is_calibrated:
            if not calibrate:
                # lerobot-calibrate calls connect(calibrate=False) before calibrate().
                self.bus.disable_torque()
                return
            self.calibrate()
        self.configure()

    def setup_motors(self) -> None:
        for name in reversed(self.bus.motors):
            input(
                f"{self.id}: power OFF, connect ONLY this device's '{name}' motor; "
                "power ON, then press ENTER: "
            )
            self.bus.setup_motor(name)
            print(f"{self.id}: {name} is motor ID {self.bus.motors[name].id}.")

    def prepare_action(self, action: dict[str, Any]) -> tuple[dict[str, int], dict[str, float]]:
        """Validate completely before any goal write, then calculate raw targets."""
        goal = validate_action(action, JOINT_FEATURES)
        requested_rotation = goal["rotation.pos"]
        if not self._continuous_rotation:
            degrees_to_ticks(requested_rotation)
        if not self.config.rotation_min_deg <= requested_rotation <= self.config.rotation_max_deg:
            raise ValueError("Rotation target is outside the configured working window.")
        if not self._continuous_rotation:
            self._target_guard.check(requested_rotation)
        present = self._read_positions()
        if not self._continuous_rotation and self.config.stop_on_encoder_wrap and abs(requested_rotation - present["rotation.pos"]) > 180:
            raise ValueError("Rotation target differs by >180 degrees. Roughly align leader/follower first.")
        limits = self.config.max_relative_target
        caps = dict.fromkeys(["rotation", "gripper"], limits) if not isinstance(limits, dict) else limits
        goal["rotation.pos"] = clamp_relative(requested_rotation, present["rotation.pos"], caps["rotation"])
        goal["gripper.pos"] = min(100.0, max(0.0, goal["gripper.pos"]))
        goal["gripper.pos"] = clamp_relative(goal["gripper.pos"], present["gripper.pos"], caps["gripper"])
        cal = self.calibration["gripper"]
        raw = {
            "gripper": gripper_to_ticks(goal["gripper.pos"], cal.range_min, cal.range_max, bool(cal.drive_mode)),
        }
        if not self._continuous_rotation:
            raw["rotation"] = degrees_to_ticks(goal["rotation.pos"])
        sent = {
            "rotation.pos": goal["rotation.pos"] if self._continuous_rotation else ticks_to_degrees(raw["rotation"]),
            "gripper.pos": ticks_to_gripper(raw["gripper"], cal.range_min, cal.range_max, bool(cal.drive_mode)),
        }
        return raw, sent

    def _write_prepared(self, prepared: tuple[dict[str, int], dict[str, float]]) -> dict[str, float]:
        raw, sent = prepared
        with self._bus_lock:
            if self._continuous_rotation:
                self._rotation_loop.snapshot()
            self.bus.sync_write("Goal_Position", raw, normalize=False)
            if self._continuous_rotation:
                self._rotation_loop.set_target(sent["rotation.pos"])
        return sent

    def _disconnect_resources(self) -> None:
        # Close every resource even after a partially failed connect or camera read.
        errors: list[Exception] = []
        try:
            self._stop_rotation_worker()
        except Exception as exc:
            errors.append(exc)
        for camera in getattr(self, "cameras", {}).values():
            if camera.is_connected:
                try:
                    camera.disconnect()
                except Exception as exc:
                    errors.append(exc)
        worker_running = self._rotation_loop is not None and self._rotation_loop.is_running
        if worker_running:
            errors.append(RuntimeError("Serial bus left open because the rotation worker is still running."))
        elif self.bus.is_connected:
            acquired = self._bus_lock.acquire(timeout=0.5)
            if not acquired:
                errors.append(RuntimeError("Serial bus lock unavailable during disconnect."))
            else:
                try:
                    self.bus.disconnect(disable_torque=self.config.disable_torque_on_disconnect)
                except Exception as exc:
                    errors.append(exc)
                    # A torque-off failure must not leave the serial handle open.
                    try:
                        self.bus.disconnect(disable_torque=False)
                    except Exception as close_exc:
                        errors.append(close_exc)
                finally:
                    self._bus_lock.release()
        self._position_guard.reset()
        self._target_guard.reset()
        if errors:
            raise RuntimeError(f"Cleanup failed for {self.id}: {errors}") from errors[0]
