"""Native registration and unchanged CLI contracts; no real hardware connections."""

import ast
import subprocess
import sys
import unittest
from pathlib import Path

import draccus

ROOT = Path(__file__).resolve().parents[3]


@unittest.skipUnless(hasattr(draccus, "parse"), "Requires real draccus, not offline import substitutes")
class NativeIntegrationTests(unittest.TestCase):
    def test_fresh_import_registers_all_types_without_plugin_discovery(self):
        code = """
from lerobot.robots.config import RobotConfig
from lerobot.teleoperators.config import TeleoperatorConfig
assert {'twister', 'bimanual_harvesting'} <= RobotConfig.get_known_choices().keys()
assert {'twister_leader', 'bimanual_harvesting_leader'} <= TeleoperatorConfig.get_known_choices().keys()
assert not any(name.startswith('lerobot_robot_harvesting') for name in __import__('sys').modules)
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", "import sys; sys.path.insert(0, " + repr(str(ROOT / "src")) + ");" + code],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_replay_and_full_rollout_configs_accept_both_embodiments(self):
        from lerobot.policies.act.configuration_act import ACTConfig  # noqa: F401
        from lerobot.rollout.configs import RolloutConfig
        from lerobot.scripts.lerobot_replay import ReplayConfig

        for kind, ports in [
            ("twister", ["--robot.port=FAKE_T"]),
            ("bimanual_harvesting", ["--robot.left_arm_config.port=FAKE_T", "--robot.right_arm_config.port=FAKE_A"]),
        ]:
            with self.subTest(robot=kind):
                hardware = [f"--robot.type={kind}", "--robot.id=integration"] + ports
                replay = draccus.parse(ReplayConfig, args=hardware + [
                    "--dataset.repo_id=local/test", "--dataset.episode=2", "--play_sounds=false",
                ])
                self.assertEqual(replay.robot.type, kind)
                self.assertEqual(replay.dataset.episode, 2)
                rollout = draccus.parse(RolloutConfig, args=hardware + [
                    "--policy.type=act", "--policy.device=cpu", "--strategy.type=base",
                    "--fps=20", "--duration=3", "--return_to_initial_position=false", "--play_sounds=false",
                ])
                self.assertEqual(rollout.robot.type, kind)
                self.assertEqual(rollout.fps, 20)
                self.assertEqual(rollout.duration, 3)

    def test_native_cli_preserves_custom_and_standard_options(self):
        from lerobot.scripts.lerobot_teleoperate import TeleoperateConfig

        cfg = draccus.parse(TeleoperateConfig, args=[
            "--robot.type=bimanual_harvesting", "--robot.id=follower",
            "--robot.left_arm_config.port=FAKE_T", "--robot.right_arm_config.port=FAKE_A",
            "--robot.left_arm_config.rotation_kp=1.5", "--robot.left_arm_config.rotation_speed=300",
            "--robot.left_arm_config.max_relative_target={rotation: 10.0, gripper: 5.0}",
            "--robot.right_arm_config.num_read_retries=3",
            "--teleop.type=bimanual_harvesting_leader", "--teleop.id=leader",
            "--teleop.left_arm_config.port=FAKE_L", "--teleop.right_arm_config.port=FAKE_R",
            "--fps=25", "--display_data=false",
        ])
        self.assertEqual(cfg.robot.left_arm_config.rotation_kp, 1.5)
        self.assertEqual(cfg.robot.left_arm_config.max_relative_target, {"rotation": 10.0, "gripper": 5.0})
        self.assertEqual(cfg.robot.right_arm_config.num_read_retries, 3)
        self.assertEqual(cfg.fps, 25)


class JointLimitContractTests(unittest.TestCase):
    def test_joint_limit_command_uses_feature_order_without_single_bus(self):
        source = (ROOT / "src/lerobot/scripts/lerobot_find_joint_limits.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        assignment = next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == "joint_positions" for target in node.targets))
        class Robot:
            action_features = {"twister_rotation.pos": float, "arm_gripper.pos": float}
        class Numpy:
            array = staticmethod(list)
        namespace = {"robot": Robot(), "np": Numpy(),
                     "observation": {"arm_gripper.pos": 25.0, "twister_rotation.pos": 390.0, "front": object()}}
        exec(compile(ast.Module(body=[assignment], type_ignores=[]), "joint_limit_order", "exec"), namespace)
        self.assertEqual(namespace["joint_positions"], [390.0, 25.0])


if __name__ == "__main__":
    unittest.main()
