"""Check the documented native CLI with installed dependencies; never connect hardware."""

import re
import shlex
from pathlib import Path


def cli_examples(readme: Path) -> list[tuple[str, list[str]]]:
    """Tokenize the simple PowerShell examples after joining continuation lines."""
    examples = []
    for block in re.findall(r"```powershell\n(.*?)\n```", readme.read_text(), re.DOTALL):
        block = re.sub(r"`[ \t]*\r?\n", " ", block)
        for line in block.splitlines():
            if not line.strip().startswith("lerobot-"):
                continue
            tokens = shlex.split(line, comments=True)
            if tokens:
                examples.append((tokens[0], tokens[1:]))
    return examples


def main() -> None:
    # Imports are delayed so the documentation token helper needs only stdlib.
    import draccus
    from dataclasses import dataclass

    from lerobot.cameras.opencv import OpenCVCameraConfig  # noqa: F401 -- register cameras
    from lerobot.robots.config import RobotConfig
    from lerobot.robots.utils import make_robot_from_config
    from lerobot.scripts.lerobot_calibrate import CalibrateConfig
    from lerobot.scripts.lerobot_replay import ReplayConfig
    from lerobot.scripts.lerobot_record import RecordConfig
    from lerobot.scripts.lerobot_setup_motors import SetupConfig
    from lerobot.scripts.lerobot_teleoperate import TeleoperateConfig
    from lerobot.teleoperators.config import TeleoperatorConfig
    from lerobot.teleoperators.utils import make_teleoperator_from_config

    @dataclass
    class RolloutHardware:
        robot: RobotConfig | None = None
        teleop: TeleoperatorConfig | None = None

    # Check native registration without calling third-party plugin discovery.
    assert "twister" in RobotConfig.get_known_choices(), "Built-in Twister config was not registered."
    assert "bimanual_harvesting" in RobotConfig.get_known_choices()
    assert "twister_leader" in TeleoperatorConfig.get_known_choices()
    assert "bimanual_harvesting_leader" in TeleoperatorConfig.get_known_choices()
    classes = {"lerobot-setup-motors": SetupConfig, "lerobot-calibrate": CalibrateConfig,
               "lerobot-teleoperate": TeleoperateConfig, "lerobot-record": RecordConfig,
               "lerobot-replay": ReplayConfig}
    count = 0
    for executable, args in cli_examples(Path(__file__).resolve().parents[2] / "docs" / "harvesting" / "README.md"):
        if "--help" in args:
            continue
        if executable == "lerobot-rollout":
            # Parse real hardware arguments without loading a not-yet-trained checkpoint.
            args = [arg for arg in args if arg.startswith(("--robot.", "--teleop."))]
            cfg = draccus.parse(RolloutHardware, args=args)
            label = "rollout hardware only"
        elif executable in classes:
            cfg = draccus.parse(classes[executable], args=args)
            label = executable
        else:
            continue
        robot_cfg, teleop_cfg = getattr(cfg, "robot", None), getattr(cfg, "teleop", None)
        robot = make_robot_from_config(robot_cfg) if robot_cfg is not None else None
        teleop = make_teleoperator_from_config(teleop_cfg) if teleop_cfg is not None else None
        if robot is not None:
            assert not robot.is_connected
            assert set(robot.action_features) <= set(robot.observation_features)
        if teleop is not None:
            assert not teleop.is_connected
        if robot is not None and teleop is not None:
            assert list(robot.action_features) == list(teleop.action_features)
            robot_twister = getattr(robot, "twister", robot)
            leader_twister = getattr(teleop, "twister", teleop)
            assert robot_twister.config.rotation_control == leader_twister.config.rotation_control == "continuous"
            assert robot_twister.config.rotation_min_deg == leader_twister.config.rotation_min_deg
            assert robot_twister.config.rotation_max_deg == leader_twister.config.rotation_max_deg
        if executable == "lerobot-record":
            assert cfg.dataset.no_stamp and cfg.dataset.push_to_hub
            assert robot.observation_features["front"] == (480, 640, 3)
        count += 1
        print(f"PASS {label}: robot={getattr(robot_cfg, 'type', None)}, teleop={getattr(teleop_cfg, 'type', None)}")
    assert count >= 15, "Expected the documented hardware workflows to be parsed."
    print(f"Parsed {count} native CLI examples and checked native factories. No hardware was connected.")
    print("Training and policy checkpoint loading were not exercised.")


if __name__ == "__main__":
    main()
