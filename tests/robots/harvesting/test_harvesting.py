import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lerobot.motors import MotorCalibration
from lerobot.robots.so_follower.config_so_follower import SOFollowerConfig
from lerobot.robots.utils import make_robot_from_config
from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderConfig
from lerobot.teleoperators.utils import make_teleoperator_from_config

from lerobot.robots.bimanual_harvesting.bimanual_harvesting import BimanualHarvesting
from lerobot.robots.bimanual_harvesting.config_bimanual_harvesting import BimanualHarvestingConfig
from lerobot.teleoperators.bimanual_harvesting_leader.bimanual_harvesting_leader import BimanualHarvestingLeader
from lerobot.teleoperators.bimanual_harvesting_leader.config_bimanual_harvesting_leader import BimanualHarvestingLeaderConfig
from lerobot.robots.twister.twister import Twister
from lerobot.robots.twister.config_twister import TwisterConfig, TwisterHardwareConfig
from lerobot.teleoperators.twister_leader.twister_leader import TwisterLeader
from lerobot.teleoperators.twister_leader.config_twister_leader import TwisterLeaderConfig
from lerobot.robots.twister.control import (
    BoundaryGuard,
    EncoderBoundaryError,
    MAX_ROTATION_DEG,
    degrees_to_ticks,
    gripper_to_ticks,
    ticks_to_degrees,
    ticks_to_gripper,
)
from lerobot.robots.bimanual_harvesting.simulation import (
    HARVESTING_ORDER,
    angle_to_sim_radians,
    gripper_to_sim_radians,
    ordered_vector,
    sim_radians_to_angle,
)

from fakes import FakeBus, FakeCamera


class ControlTests(unittest.TestCase):
    def test_all_encoder_positions_roundtrip(self):
        for ticks in range(4096):
            self.assertEqual(degrees_to_ticks(ticks_to_degrees(ticks)), ticks)

    def test_multiturn_is_rejected(self):
        for angle in [-1, 360, 375, 720, math.inf, math.nan]:
            with self.assertRaises(ValueError):
                degrees_to_ticks(angle)

    def test_encoder_out_of_range_is_rejected(self):
        for value in [-1, 4096, 65535]:
            with self.assertRaises(EncoderBoundaryError):
                ticks_to_degrees(value)

    def test_more_than_180_degree_total_travel_is_allowed(self):
        guard = BoundaryGuard()
        for angle in range(20, 331, 10):
            guard.check(angle)
        self.assertFalse(guard.faulted)

    def test_boundary_fault_is_latched_in_both_directions(self):
        for start, end in [(359, 0), (0, 359)]:
            guard = BoundaryGuard()
            guard.check(start)
            with self.assertRaises(EncoderBoundaryError):
                guard.check(end)
            with self.assertRaises(EncoderBoundaryError):
                guard.check(start)
            guard.reset()
            guard.check(end)

    def test_gripper_endpoint_and_inversion(self):
        for inverted in [False, True]:
            for percentage in [0, 25, 50, 100]:
                ticks = gripper_to_ticks(percentage, 1000, 3000, inverted)
                self.assertAlmostEqual(ticks_to_gripper(ticks, 1000, 3000, inverted), percentage)

    def test_simulation_direct_drive_angle_roundtrip(self):
        for direction in [-1, 1]:
            value = angle_to_sim_radians(390, start_radians=0.2, direction=direction)
            self.assertAlmostEqual(abs(value - 0.2), math.radians(390))
            self.assertAlmostEqual(sim_radians_to_angle(value, start_radians=0.2,
                                                       direction=direction), 390)

    def test_simulation_gripper(self):
        self.assertAlmostEqual(gripper_to_sim_radians(25, at_zero_radians=0,
                                                    at_hundred_radians=1), 0.25)

    def test_simulation_feature_order(self):
        values = {key: float(i) for i, key in enumerate(HARVESTING_ORDER)}
        self.assertEqual(ordered_vector(dict(reversed(list(values.items()))), HARVESTING_ORDER),
                         list(range(8)))

    def test_invalid_configuration(self):
        for fields in [dict(gripper_motor_id=1), dict(rotation_speed=0), dict(acceleration=999),
                       dict(rotation_min_deg=-1), dict(max_relative_target={"rotation": 5}),
                       dict(rotation_max_deg=math.nan), dict(rotation_torque_limit=2000)]:
            settings = {"rotation_min_deg": 0, "rotation_max_deg": MAX_ROTATION_DEG, **fields}
            with self.assertRaises(ValueError):
                TwisterConfig(port="FAKE", rotation_control="single_turn", **settings)


class DeviceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cal_dir = Path(self.tmp.name)
        FakeBus.instances.clear()
        for target in ["lerobot.robots.twister.device.FeetechMotorsBus",
                       "lerobot.robots.so_follower.so_follower.FeetechMotorsBus",
                       "lerobot.teleoperators.so_leader.so_leader.FeetechMotorsBus"]:
            patcher = patch(target, FakeBus)
            patcher.start()
            self.addCleanup(patcher.stop)

    def calibrate_fake(self, device):
        device.calibration = {
            "rotation": MotorCalibration(1, 0, 0, 0, 4095),
            "gripper": MotorCalibration(2, 0, 0, 1000, 3000),
        }
        device.bus.calibration = device.calibration

    def robot(self, **kwargs):
        robot = Twister(TwisterConfig(port="FAKE_R", id="robot", calibration_dir=self.cal_dir,
                                      rotation_control="single_turn", rotation_min_deg=0,
                                      rotation_max_deg=MAX_ROTATION_DEG, **kwargs))
        self.calibrate_fake(robot)
        self.addCleanup(robot.disconnect)
        return robot

    def pair(self):
        cfg = BimanualHarvestingConfig(id="pair", calibration_dir=self.cal_dir,
                                      left_arm_config=TwisterHardwareConfig(port="FAKE_T", rotation_control="single_turn",
                                                                    rotation_min_deg=0,
                                                                    rotation_max_deg=MAX_ROTATION_DEG),
                                      right_arm_config=SOFollowerConfig(port="FAKE_A"))
        robot = BimanualHarvesting(cfg)
        self.calibrate_fake(robot.twister)
        robot.arm.bus.calibration = {"dummy": True}
        self.addCleanup(robot.disconnect)
        return robot

    def test_factory_registration_standalone(self):
        robot = make_robot_from_config(TwisterConfig(port="FAKE", calibration_dir=self.cal_dir))
        leader = make_teleoperator_from_config(TwisterLeaderConfig(port="FAKE_L", calibration_dir=self.cal_dir))
        self.assertIsInstance(robot, Twister)
        self.assertIsInstance(leader, TwisterLeader)
        self.assertEqual(robot.action_features, leader.action_features)

    def test_factory_registration_pair(self):
        robot = self.pair()
        leader_cfg = BimanualHarvestingLeaderConfig(id="leader", calibration_dir=self.cal_dir,
                                                   left_arm_config=TwisterHardwareConfig(port="FAKE_TL"),
                                                   right_arm_config=SOLeaderConfig(port="FAKE_AL"))
        leader = make_teleoperator_from_config(leader_cfg)
        made = make_robot_from_config(robot.config)
        self.assertIsInstance(made, BimanualHarvesting)
        self.assertIsInstance(leader, BimanualHarvestingLeader)
        self.assertEqual(list(robot.action_features), list(leader.action_features))
        self.assertEqual(tuple(robot.action_features), HARVESTING_ORDER)

    def test_pair_forwards_arbitrary_ports_and_twister_options(self):
        robot = make_robot_from_config(BimanualHarvestingConfig(
            id="my_pair", calibration_dir=self.cal_dir,
            left_arm_config=TwisterHardwareConfig(
                port="COM42", rotation_motor_id=7, gripper_motor_id=9, rotation_speed=300,
            ),
            right_arm_config=SOFollowerConfig(port="COM43", position_p_coefficient=20),
        ))
        self.assertEqual(robot.left_arm.bus.port, "COM42")
        self.assertEqual(robot.right_arm.bus.port, "COM43")
        self.assertEqual(robot.left_arm.bus.motors["rotation"].id, 7)
        self.assertEqual(robot.left_arm.bus.motors["gripper"].id, 9)
        self.assertEqual(robot.left_arm.config.rotation_speed, 300)
        self.assertEqual(robot.right_arm.config.position_p_coefficient, 20)
        self.assertEqual(robot.left_arm.id, "my_pair_twister")
        self.assertEqual(robot.right_arm.id, "my_pair_arm")

    def test_feature_contract_is_available_before_connect(self):
        robot = self.robot()
        self.assertFalse(robot.is_connected)
        self.assertEqual(robot.action_features, {"rotation.pos": float, "gripper.pos": float})
        self.assertEqual(robot.action_features, robot.observation_features)

    def test_connect_seeds_current_position_before_torque(self):
        robot = self.robot()
        robot.bus.positions["rotation"] = 1800
        robot.connect()
        ops = robot.bus.operations
        hold = next(i for i, op in enumerate(ops) if op[0] == "goal")
        torque = next(i for i, op in enumerate(ops) if op == ("torque", True))
        self.assertLess(hold, torque)
        self.assertEqual(ops[hold][2]["rotation"], 1800)
        self.assertNotEqual(ops[hold][2]["rotation"], 0)

    def test_leader_remains_passive(self):
        leader = TwisterLeader(TwisterLeaderConfig(port="FAKE", id="leader", calibration_dir=self.cal_dir,
                                                  rotation_control="single_turn", rotation_min_deg=0,
                                                  rotation_max_deg=MAX_ROTATION_DEG))
        self.calibrate_fake(leader)
        leader.connect()
        self.addCleanup(leader.disconnect)
        self.assertNotIn(("torque", True), leader.bus.operations)
        self.assertEqual(leader.get_action()["rotation.pos"], 180)

    def test_calibration_cli_connect_false_is_supported(self):
        robot = Twister(TwisterConfig(port="FAKE", calibration_dir=self.cal_dir))
        robot.connect(calibrate=False)
        self.addCleanup(robot.disconnect)
        self.assertTrue(robot.is_connected)
        self.assertNotIn(("torque", True), robot.bus.operations)
        with patch("builtins.input", return_value=""):
            robot.calibrate()
        self.assertTrue(robot.is_calibrated)
        self.assertTrue(robot.calibration_fpath.exists())

    def test_action_encoding_and_returned_command(self):
        robot = self.robot()
        robot.connect()
        sent = robot.send_action({"rotation.pos": 195, "gripper.pos": 25})
        self.assertEqual(robot.bus.operations[-1][2], {"rotation": degrees_to_ticks(195), "gripper": 1500})
        self.assertAlmostEqual(sent["rotation.pos"], 195, delta=0.05)
        self.assertEqual(sent["gripper.pos"], 25)

    def test_optional_relative_target_cap(self):
        robot = self.robot(max_relative_target={"rotation": 5, "gripper": 3})
        robot.connect()
        sent = robot.send_action({"rotation.pos": 200, "gripper.pos": 100})
        self.assertAlmostEqual(sent["rotation.pos"], 185, delta=0.05)
        self.assertAlmostEqual(sent["gripper.pos"], 55.4, delta=0.1)

    def test_invalid_action_never_writes_goals(self):
        robot = self.robot()
        robot.connect()
        for action in [{"rotation.pos": 181}, {"rotation.pos": math.nan, "gripper.pos": 10},
                       {"rotation.pos": 375, "gripper.pos": 10},
                       {"rotation.pos": 181, "gripper.pos": 10, "extra.pos": 10}]:
            before = len(robot.bus.operations)
            with self.assertRaises(ValueError):
                robot.send_action(action)
            self.assertEqual(len(robot.bus.operations), before)

    def test_observed_wrap_stops(self):
        robot = self.robot()
        robot.bus.positions["rotation"] = 4000
        robot.connect()
        robot.get_observation()
        robot.bus.positions["rotation"] = 5
        with self.assertRaises(EncoderBoundaryError):
            robot.get_observation()

    def test_requested_wrap_stops_before_write(self):
        robot = self.robot()
        robot.bus.positions["rotation"] = 4000
        robot.connect()
        before = len(robot.bus.operations)
        with self.assertRaises(EncoderBoundaryError):
            robot.send_action({"rotation.pos": 1, "gripper.pos": 50})
        self.assertEqual(len(robot.bus.operations), before)

    def test_camera_feature_and_frame_shape(self):
        camera = FakeCamera()
        robot = self.robot()
        robot.cameras["front"] = camera
        robot.connect()
        obs = robot.get_observation()
        self.assertEqual(robot.observation_features["front"], obs["front"].shape)
        self.assertEqual(set(obs), set(robot.observation_features))

    def test_camera_connect_failure_closes_bus_and_camera(self):
        robot = self.robot()
        camera = FakeCamera(fail=True)
        robot.cameras["front"] = camera
        with self.assertRaises(OSError):
            robot.connect()
        self.assertFalse(robot.bus.is_connected)
        self.assertFalse(camera.is_connected)

    def test_torque_disable_failure_still_closes_serial(self):
        robot = self.robot()
        robot.connect()
        robot.bus.fail_disconnect = True
        with self.assertRaises(RuntimeError):
            robot.disconnect()
        self.assertFalse(robot.bus.is_connected)

    def test_pair_routes_eight_targets(self):
        robot = self.pair()
        robot.connect()
        values = {key: 0.0 for key in robot.action_features}
        values.update({"twister_rotation.pos": 190, "twister_gripper.pos": 50})
        sent = robot.send_action(values)
        self.assertEqual(set(sent), set(values))
        self.assertEqual(len(robot.arm.bus.operations[-1][2]), 6)
        self.assertEqual(set(robot.twister.bus.operations[-1][2]), {"rotation", "gripper"})

    def test_pair_rejects_invalid_arm_before_twister_write(self):
        robot = self.pair()
        robot.connect()
        values = dict.fromkeys(robot.action_features, 0.0)
        values["arm_elbow_flex.pos"] = math.inf
        before = len(robot.twister.bus.operations)
        with self.assertRaises(ValueError):
            robot.send_action(values)
        self.assertEqual(len(robot.twister.bus.operations), before)

    def test_pair_partial_connect_closes_both_devices(self):
        robot = self.pair()
        robot.arm.bus.fail_connect = True
        with self.assertRaises(OSError):
            robot.connect()
        self.assertFalse(robot.twister.bus.is_connected)
        self.assertFalse(robot.arm.bus.is_connected)

    def test_pair_ids_reuse_standalone_calibrations(self):
        robot = self.pair()
        self.assertEqual(robot.twister.id, "pair_twister")
        self.assertEqual(robot.arm.id, "pair_arm")
        self.assertEqual(robot.twister.calibration_fpath.name, "pair_twister.json")


if __name__ == "__main__":
    unittest.main()
