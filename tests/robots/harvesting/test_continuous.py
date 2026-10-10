"""Direct-drive cumulative motion, feedback control, worker and stop regression tests."""

import math
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from lerobot.motors import MotorCalibration
from lerobot.robots.so_follower.config_so_follower import SOFollowerConfig

from lerobot.robots.bimanual_harvesting.bimanual_harvesting import BimanualHarvesting
from lerobot.robots.bimanual_harvesting.config_bimanual_harvesting import BimanualHarvestingConfig
from lerobot.robots.twister.twister import Twister
from lerobot.robots.twister.config_twister import TwisterConfig, TwisterHardwareConfig
from lerobot.teleoperators.twister_leader.twister_leader import TwisterLeader
from lerobot.teleoperators.twister_leader.config_twister_leader import TwisterLeaderConfig
from lerobot.robots.twister.continuous import ContinuousRotationLoop
from lerobot.robots.twister.control import (
    DEGREES_PER_TICK,
    PositionVelocityController,
    RotationTrackingError,
    UnwrappedEncoder,
)

from fakes import FakeBus, FakeCamera


def raw_angle(degrees):
    return round(degrees / DEGREES_PER_TICK) % 4096


class TrackingTests(unittest.TestCase):
    def tracker(self):
        return UnwrappedEncoder(max_gap_s=0.15, max_speed_deg_s=720)

    def test_200_alignment_plus_190_twist_is_390(self):
        tracker = self.tracker()
        for i, angle in enumerate(range(0, 391, 5)):
            value = tracker.update(raw_angle(angle), i * 0.02)
        self.assertAlmostEqual(value, 390, delta=0.1)

    def test_arbitrary_start_pose_is_relative_zero(self):
        tracker = self.tracker()
        self.assertEqual(tracker.update(raw_angle(247), 0), 0)
        for i, offset in enumerate(range(5, 391, 5), start=1):
            value = tracker.update(raw_angle(247 + offset), i * 0.02)
        self.assertAlmostEqual(value, 390, delta=0.1)

    def test_crossing_boundary_adds_two_degrees(self):
        tracker = self.tracker()
        tracker.update(raw_angle(359), 0)
        self.assertAlmostEqual(tracker.update(raw_angle(1), 0.02), 2, delta=0.1)

    def test_reverse_crossing_subtracts_two_degrees(self):
        tracker = self.tracker()
        tracker.update(raw_angle(1), 0)
        self.assertAlmostEqual(tracker.update(raw_angle(359), 0.02), -2, delta=0.1)

    def test_reverse_from_390_back_to_zero(self):
        tracker = self.tracker()
        sequence = list(range(0, 391, 5)) + list(range(385, -1, -5))
        for i, angle in enumerate(sequence):
            value = tracker.update(raw_angle(angle), i * 0.02)
        self.assertAlmostEqual(value, 0, delta=0.1)

    def test_multiple_forward_and_reverse_turns(self):
        for direction in [-1, 1]:
            tracker = self.tracker()
            for i, angle in enumerate(range(0, 1081, 5)):
                value = tracker.update(raw_angle(direction * angle), i * 0.02)
            self.assertAlmostEqual(value, direction * 1080, delta=0.1)

    def test_gap_fault_is_latched_even_if_raw_returns_same(self):
        tracker = self.tracker()
        tracker.update(1234, 0)
        with self.assertRaises(RotationTrackingError):
            tracker.update(1234, 1)
        with self.assertRaises(RotationTrackingError):
            tracker.update(1234, 1.01)

    def test_impossible_speed_is_rejected(self):
        tracker = self.tracker()
        tracker.update(0, 0)
        with self.assertRaises(RotationTrackingError):
            tracker.update(raw_angle(150), 0.02)

    def test_half_turn_is_ambiguous(self):
        tracker = self.tracker()
        tracker.update(0, 0)
        with self.assertRaises(RotationTrackingError):
            tracker.update(2048, 0.02)

    def test_unwrapping_does_not_invent_extra_turns_from_identical_samples(self):
        tracker = self.tracker()
        for i in range(100):
            value = tracker.update(1234, i * 0.02)
        self.assertEqual(value, 0)

    def test_tracking_bounds_are_validated(self):
        with self.assertRaises(ValueError):
            UnwrappedEncoder(max_gap_s=1, max_speed_deg_s=720)


class PositionControllerTests(unittest.TestCase):
    def controller(self):
        return PositionVelocityController(2, 400, 0.5, 1)

    def test_cumulative_target_across_360_keeps_forward_command(self):
        controller = self.controller()
        controller.set_target(390, 0)
        self.assertGreater(controller.velocity(359, 0.1), 0)
        self.assertGreater(controller.velocity(361, 0.2), 0)

    def test_speed_is_capped(self):
        controller = self.controller()
        controller.set_target(390, 0)
        self.assertEqual(controller.velocity(0, 0.1), 400)

    def test_reverse_velocity_sign_keeps_position_error_semantics(self):
        controller = PositionVelocityController(2, 400, 0.5, 1, direction=-1)
        controller.set_target(390, 0)
        self.assertEqual(controller.velocity(0, 0.1), -400)
        self.assertGreater(controller.velocity(392, 0.1), 0)

    def test_overshoot_commands_return_direction(self):
        controller = self.controller()
        controller.set_target(390, 0)
        self.assertLess(controller.velocity(392, 0.1), 0)

    def test_deadband_stops(self):
        controller = self.controller()
        controller.set_target(390, 0)
        self.assertEqual(controller.velocity(390.4, 0.1), 0)

    def test_watchdog_stops_old_target_and_fresh_command_resumes(self):
        controller = self.controller()
        controller.set_target(390, 0)
        self.assertEqual(controller.velocity(200, 1.1), 0)
        controller.set_target(390, 1.2)
        self.assertGreater(controller.velocity(200, 1.21), 0)

    def test_passive_leader_never_commands_rotation(self):
        controller = self.controller()
        controller.set_target(390, 0)
        self.assertEqual(controller.velocity(0, 0.1, enabled=False), 0)

    def test_direct_drive_ideal_plant_reaches_200_then_390(self):
        controller = self.controller()
        tracker = UnwrappedEncoder()
        position, now = 0.0, 0.0
        tracker.update(raw_angle(position), now)
        observed_angles = []
        for target in [200, 390]:
            for _ in range(1500):
                controller.set_target(target, now)
                velocity = controller.velocity(position, now)
                position += velocity * DEGREES_PER_TICK * 0.02
                now += 0.02
                observed = tracker.update(raw_angle(position), now)
                observed_angles.append(observed)
                if abs(position - target) <= 0.5:
                    break
            self.assertAlmostEqual(position, target, delta=0.5)
        self.assertGreater(max(observed_angles), 389)
        self.assertTrue(all(b >= a - 0.1 for a, b in zip(observed_angles, observed_angles[1:])))


class ContinuousDeviceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch_bus = patch("lerobot.robots.twister.device.FeetechMotorsBus", FakeBus)
        self.patch_bus.start()
        self.addCleanup(self.patch_bus.stop)

    def device(self, leader=False):
        cfg_cls, cls = (TwisterLeaderConfig, TwisterLeader) if leader else (TwisterConfig, Twister)
        device = cls(cfg_cls(port="FAKE", id="continuous", calibration_dir=Path(self.tmp.name)))
        device.calibration = {"rotation": MotorCalibration(1, 0, 0, 0, 4095),
                              "gripper": MotorCalibration(2, 0, 0, 1000, 3000)}
        device.bus.calibration = device.calibration
        self.addCleanup(device.disconnect)
        return device

    def test_default_configuration_is_cumulative_direct_drive(self):
        robot = self.device()
        self.assertEqual(robot.config.rotation_control, "continuous")
        self.assertLess(robot.config.rotation_min_deg, 0)
        self.assertGreater(robot.config.rotation_max_deg, 390)

    def test_invalid_continuous_tracking_configuration(self):
        for fields in [{"max_tracking_gap_s": 1}, {"max_tracking_speed_deg_s": 2000},
                       {"rotation_min_deg": 1}, {"rotation_velocity_sign": 0},
                       {"rotation_speed": "400"}, {"rotation_speed": 10000}]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                TwisterConfig(port="FAKE", **fields)

    def test_configure_uses_velocity_for_rotation_position_for_gripper(self):
        robot = self.device()
        robot.connect()
        writes = [op for op in robot.bus.operations if op[0] == "write"]
        self.assertIn(("write", "Operating_Mode", "rotation", 1), writes)
        self.assertIn(("write", "Operating_Mode", "gripper", 0), writes)
        self.assertEqual(robot.get_observation()["rotation.pos"], 0)
        self.assertFalse(any(op[0] == "goal" and "rotation" in op[2] for op in robot.bus.operations))

    def test_390_degree_action_is_accepted_without_modulo(self):
        robot = self.device()
        robot.connect()
        sent = robot.send_action({"rotation.pos": 390, "gripper.pos": 25})
        self.assertEqual(sent["rotation.pos"], 390)
        self.assertEqual(robot._rotation_loop.controller.target, 390)
        self.assertEqual(robot.bus.operations[-1][2], {"gripper": 1500})

    def test_large_negative_target_is_accepted(self):
        robot = self.device()
        robot.connect()
        sent = robot.send_action({"rotation.pos": -390, "gripper.pos": 25})
        self.assertEqual(sent["rotation.pos"], -390)

    def test_target_outside_window_never_updates_motor(self):
        robot = self.device()
        robot.connect()
        for value in [-721, 721, math.nan]:
            with self.assertRaises(ValueError):
                robot.send_action({"rotation.pos": value, "gripper.pos": 25})
        self.assertIsNone(robot._rotation_loop.controller.last_command)

    def test_leader_sampler_is_running_but_passive(self):
        leader = self.device(leader=True)
        leader.connect()
        self.assertTrue(leader._rotation_loop._thread.is_alive())
        self.assertFalse(leader._rotation_loop.enabled)
        self.assertNotIn(("torque", True), leader.bus.operations)
        self.assertEqual(leader.get_action()["rotation.pos"], 0)

    def test_worker_stop_precedes_serial_disconnect(self):
        robot = self.device()
        robot.connect()
        loop = robot._rotation_loop
        robot.disconnect()
        self.assertFalse(loop._thread.is_alive())
        stop = max(i for i, op in enumerate(robot.bus.operations) if op == ("write", "Goal_Velocity", "rotation", 0))
        disconnect = next(i for i, op in enumerate(robot.bus.operations) if op[0] == "disconnect")
        self.assertLess(stop, disconnect)

    def test_worker_read_failure_stops_and_faults(self):
        robot = self.device()
        robot.connect()
        loop = robot._rotation_loop
        with patch.object(robot.bus, "sync_read", side_effect=OSError("Read failed")):
            loop._thread.join(timeout=0.5)
        self.assertFalse(loop._thread.is_alive())
        with self.assertRaises(RotationTrackingError):
            robot.get_observation()
        self.assertIn(("write", "Goal_Velocity", "rotation", 0), robot.bus.operations)

    def test_manual_sampling_tracks_leader_390_without_thread_timing_assumptions(self):
        robot = self.device()
        robot.bus.connect()
        now = [0.0]
        loop = ContinuousRotationLoop(robot.bus, threading.RLock(), robot.config, actuate=False,
                                      clock=lambda: now[0])
        for i, angle in enumerate(range(0, 391, 5)):
            now[0] = i * 0.02
            robot.bus.positions["rotation"] = raw_angle(247 + angle)
            loop.sample_once()
        self.assertAlmostEqual(loop.snapshot()[0], 390, delta=0.1)
        loop.stop()

    def test_stale_snapshot_is_a_latched_fault(self):
        robot = self.device()
        robot.bus.connect()
        now = [0.0]
        loop = ContinuousRotationLoop(robot.bus, threading.RLock(), robot.config, actuate=False,
                                      clock=lambda: now[0])
        loop.sample_once()
        now[0] = 1
        with self.assertRaises(RotationTrackingError):
            loop.snapshot()
        loop.stop()

    def test_worker_watchdog_sends_zero_without_new_commands(self):
        robot = self.device()
        robot.bus.connect()
        now = [0.0]
        loop = ContinuousRotationLoop(robot.bus, threading.RLock(), robot.config, actuate=True,
                                      clock=lambda: now[0])
        loop.sample_once()
        loop.set_target(390)
        now[0] = 0.02
        loop.sample_once()
        self.assertEqual(robot.bus.operations[-1], ("write", "Goal_Velocity", "rotation", 400))
        for _ in range(51):
            now[0] += 0.02
            loop.sample_once()
        self.assertEqual(robot.bus.operations[-1], ("write", "Goal_Velocity", "rotation", 0))
        loop.stop()

    def test_stop_packet_failure_is_reported_even_after_tracking_failure(self):
        robot = self.device()
        robot.bus.connect()
        loop = ContinuousRotationLoop(robot.bus, threading.RLock(), robot.config, actuate=True)
        loop.fail(RotationTrackingError("Original encoder fault"))
        with patch.object(robot.bus, "write", side_effect=OSError("Stop packet failed")):
            with self.assertRaisesRegex(RuntimeError, "Stop packet failed"):
                loop.stop()

    def test_calibration_reuse_stops_live_worker_before_prompt(self):
        robot = self.device()
        robot.connect(calibrate=False)
        loop = robot._rotation_loop
        def answer(_prompt):
            self.assertFalse(loop.is_running)
            return ""
        with patch("builtins.input", side_effect=answer):
            robot.calibrate()
        self.assertIsNone(robot._rotation_loop)

    def test_partial_camera_connect_stops_rotation_worker(self):
        robot = self.device()
        camera = FakeCamera(fail=True)
        robot.cameras = {"front": camera}
        with self.assertRaisesRegex(OSError, "camera"):
            robot.connect()
        self.assertIsNone(robot._rotation_loop)
        self.assertFalse(robot.bus.is_connected)
        self.assertFalse(camera.is_connected)
        self.assertIn(("write", "Goal_Velocity", "rotation", 0), robot.bus.operations)

    def test_hung_worker_is_retained_and_bus_is_not_closed_under_it(self):
        robot = self.device()
        robot.bus.connect()
        worker = unittest.mock.Mock()
        worker.is_running = True
        worker.stop.side_effect = RuntimeError("Worker did not stop")
        robot._rotation_loop = worker
        with self.assertRaisesRegex(RuntimeError, "still running"):
            robot.disconnect()
        self.assertIs(robot._rotation_loop, worker)
        self.assertTrue(robot.bus.is_connected)
        worker.is_running = False
        worker.stop.side_effect = None
        robot.disconnect()

    def test_combined_robot_routes_390_degree_target_and_six_arm_joints(self):
        with patch("lerobot.robots.so_follower.so_follower.FeetechMotorsBus", FakeBus):
            robot = BimanualHarvesting(BimanualHarvestingConfig(
                id="combined", calibration_dir=Path(self.tmp.name),
                left_arm_config=TwisterHardwareConfig(port="FAKE_T"), right_arm_config=SOFollowerConfig(port="FAKE_A"),
            ))
        self.addCleanup(robot.disconnect)
        robot.twister.calibration = {"rotation": MotorCalibration(1, 0, 0, 0, 4095),
                                     "gripper": MotorCalibration(2, 0, 0, 1000, 3000)}
        robot.twister.bus.calibration = robot.twister.calibration
        robot.arm.bus.calibration = {"dummy": True}
        robot.connect()
        action = dict.fromkeys(robot.action_features, 10.0)
        action["twister_rotation.pos"] = 390
        action["twister_gripper.pos"] = 25
        sent = robot.send_action(action)
        self.assertEqual(sent["twister_rotation.pos"], 390)
        self.assertEqual(list(sent), list(robot.action_features))
        self.assertEqual(len(robot.arm.bus.operations[-1][2]), 6)
        self.assertFalse(any(op[0] == "goal" and "rotation" in op[2]
                             for op in robot.twister.bus.operations))

    def test_command_and_polling_use_the_same_serial_lock(self):
        robot = self.device()
        robot.connect()
        lock = robot._bus_lock
        original_write = robot.bus.write
        original_read = robot.bus.sync_read
        original_sync_write = robot.bus.sync_write
        def guarded(function):
            def call(*args, **kwargs):
                self.assertTrue(lock._is_owned())
                return function(*args, **kwargs)
            return call
        with patch.object(robot.bus, "write", side_effect=guarded(original_write)), \
             patch.object(robot.bus, "sync_read", side_effect=guarded(original_read)), \
             patch.object(robot.bus, "sync_write", side_effect=guarded(original_sync_write)):
            robot.send_action({"rotation.pos": 390, "gripper.pos": 25})
            robot._rotation_loop.sample_once()
            robot.disconnect()


if __name__ == "__main__":
    unittest.main()
