"""Check config field names and the actual upstream feature converter without ML imports."""

import ast
import importlib.util
import unittest
from dataclasses import fields
from pathlib import Path

from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderTeleopConfig

from lerobot.robots.bimanual_harvesting.config_bimanual_harvesting import BimanualHarvestingConfig
from lerobot.teleoperators.bimanual_harvesting_leader.config_bimanual_harvesting_leader import BimanualHarvestingLeaderConfig
from lerobot.robots.twister.config_twister import TwisterConfig, TwisterHardwareConfig
from lerobot.teleoperators.twister_leader.config_twister_leader import TwisterLeaderConfig
from lerobot.robots.bimanual_harvesting.simulation import HARVESTING_ORDER

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "src" / "lerobot"


def annotated_fields(relative_file, class_name):
    tree = ast.parse((SOURCE / relative_file).read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return {node.target.id for node in cls.body if isinstance(node, ast.AnnAssign)}


spec = importlib.util.spec_from_file_location("verify_cli_examples", ROOT / "examples" / "harvesting" / "verify_install.py")
verify_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_cli)


def cli_values(args):
    return {arg[2:].split("=", 1)[0]: arg.split("=", 1)[1] for arg in args
            if arg.startswith("--") and "=" in arg}


class SourceContractTests(unittest.TestCase):
    def test_documentation_has_native_workflows_without_preset_files(self):
        examples = verify_cli.cli_examples(ROOT / "docs" / "harvesting" / "README.md")
        self.assertGreaterEqual(len(examples), 20)
        self.assertFalse((ROOT / "configs").exists())
        self.assertFalse(any(arg.startswith("--config_path") for _, args in examples for arg in args))
        self.assertTrue({"lerobot-setup-motors", "lerobot-calibrate", "lerobot-teleoperate",
                         "lerobot-record", "lerobot-train", "lerobot-rollout"} <=
                        {name for name, _ in examples})

    def test_combined_config_matches_native_bimanual_field_names(self):
        native_robot = annotated_fields("robots/bi_so_follower/config_bi_so_follower.py", "BiSOFollowerConfig")
        native_teleop = annotated_fields("teleoperators/bi_so_leader/config_bi_so_leader.py", "BiSOLeaderConfig")
        for cls, names in [(BimanualHarvestingConfig, native_robot),
                           (BimanualHarvestingLeaderConfig, native_teleop)]:
            keys = {item.name for item in fields(cls)}
            self.assertTrue(names <= keys)
            self.assertNotIn("twister", keys)
            self.assertNotIn("arm", keys)

    def test_documented_hardware_ports_match_requested_roles(self):
        for name, args in verify_cli.cli_examples(ROOT / "docs" / "harvesting" / "README.md"):
            if name == "lerobot-train" or "--help" in args:
                continue
            data = cli_values(args)
            for prefix in ("robot", "teleop"):
                choice = data.get(f"{prefix}.type")
                if choice in ("twister", "twister_leader"):
                    self.assertEqual(data[f"{prefix}.port"], "COM16" if prefix == "robot" else "COM14")
                elif choice in ("so100_follower", "so100_leader"):
                    self.assertEqual(data[f"{prefix}.port"], "COM15" if prefix == "robot" else "COM13")
                elif choice in ("bimanual_harvesting", "bimanual_harvesting_leader"):
                    self.assertEqual(data[f"{prefix}.left_arm_config.port"], "COM16" if prefix == "robot" else "COM14")
                    self.assertEqual(data[f"{prefix}.right_arm_config.port"], "COM15" if prefix == "robot" else "COM13")

    def test_all_documented_cli_option_names_match_uploaded_version(self):
        top = {
            "lerobot-teleoperate": annotated_fields("scripts/lerobot_teleoperate.py", "TeleoperateConfig"),
            "lerobot-setup-motors": annotated_fields("scripts/lerobot_setup_motors.py", "SetupConfig"),
            "lerobot-calibrate": annotated_fields("scripts/lerobot_calibrate.py", "CalibrateConfig"),
            "lerobot-record": annotated_fields("scripts/lerobot_record.py", "RecordConfig"),
            "lerobot-train": annotated_fields("configs/train.py", "TrainPipelineConfig"),
            "lerobot-rollout": annotated_fields("rollout/configs.py", "RolloutConfig"),
        }
        device_types = {"twister": TwisterConfig, "bimanual_harvesting": BimanualHarvestingConfig,
                        "so100_follower": SOFollowerRobotConfig, "twister_leader": TwisterLeaderConfig,
                        "bimanual_harvesting_leader": BimanualHarvestingLeaderConfig,
                        "so100_leader": SOLeaderTeleopConfig}
        from lerobot.robots.so_follower.config_so_follower import SOFollowerConfig
        from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderConfig
        for executable, args in verify_cli.cli_examples(ROOT / "docs" / "harvesting" / "README.md"):
            if executable not in top:
                continue
            data = cli_values(args)
            for key in data:
                with self.subTest(executable=executable, option=key):
                    path = key.split(".")
                    self.assertIn(path[0], top[executable])
                    if path[0] in ("robot", "teleop") and len(path) > 1:
                        cls = device_types[data[f"{path[0]}.type"]]
                        self.assertIn(path[1], {f.name for f in fields(cls)} | {"type"})
                        if len(path) > 2:
                            child = TwisterHardwareConfig if path[1] == "left_arm_config" else (
                                SOFollowerConfig if path[0] == "robot" else SOLeaderConfig)
                            self.assertIn(path[2], {f.name for f in fields(child)})
                    elif path[0] == "dataset" and len(path) > 1:
                        file, cls = ("configs/default.py", "DatasetConfig") if executable == "lerobot-train" else (
                            "configs/dataset.py", "DatasetRecordConfig")
                        self.assertIn(path[1], annotated_fields(file, cls))
                    elif path[0] == "policy" and len(path) > 1:
                        allowed = annotated_fields("configs/policies.py", "PreTrainedConfig") | {"type", "path"}
                        self.assertIn(path[1], allowed)
                    elif path[0] == "wandb" and len(path) > 1:
                        self.assertIn(path[1], annotated_fields("configs/default.py", "WandBConfig"))
                    elif path[0] == "strategy" and len(path) > 1:
                        self.assertEqual(path[1], "type")

    def test_real_upstream_converter_preserves_eight_feature_names(self):
        tree = ast.parse((SOURCE / "utils" / "feature_utils.py").read_text())
        selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in
                    {"hw_to_dataset_features", "_validate_feature_names"}]
        module = ast.Module(body=selected, type_ignores=[])
        namespace = {"Mapping": dict, "Any": object, "PolicyFeature": type("PolicyFeature", (), {}),
                     "FeatureType": type("FeatureType", (), {"VISUAL": "VISUAL"}),
                     "ACTION": "action", "OBS_STR": "observation"}
        exec(compile(module, "upstream_feature_converter", "exec"), namespace)
        convert = namespace["hw_to_dataset_features"]
        hw = {**dict.fromkeys(HARVESTING_ORDER, float), "front": (480, 640, 3)}
        action = convert(hw, "action")
        observation = convert(hw, "observation")
        self.assertEqual(action["action"]["shape"], (8,))
        self.assertEqual(tuple(action["action"]["names"]), HARVESTING_ORDER)
        self.assertEqual(observation["observation.state"]["names"], list(HARVESTING_ORDER))
        self.assertEqual(observation["observation.images.front"]["shape"], (480, 640, 3))


if __name__ == "__main__":
    unittest.main()
