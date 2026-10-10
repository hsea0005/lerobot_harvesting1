# Native Twister / harvesting integration

Originally integrated on 2026-10-10 from `D:\FYP_HS\lerobot` and `LeRobot_Twister_v1 (1).zip`.
Transferred into `D:\FYP_HS\lerobotharvesting1\lerobot_harvesting1` on 2026-10-10.
The original directories and ZIP were left unchanged. The destination retains its own
Git metadata and existing source; only the custom hardware integration was transferred.
The archive's bundled upstream checkout was not overlaid on the existing local version.

## Installation and commands

Follow [README.md](README.md) for environment installation, motor setup, calibration,
teleoperation, recording, replay, training and rollout examples. Install this copy into
your chosen environment before using its `lerobot-*` executables. Simply changing
working directory does not change which editable installation those executables use.
A separate `lerobot1` environment is documented to keep the original environment intact.
No environment was installed or repointed during integration; validation selected this
copy's `src` explicitly while using your existing Python dependencies.

The distribution/import name remains `lerobot`, and all existing console entry points,
command parameter names, parser behavior, dependency extras and lockfile remain intact.
Use the existing `feetech` extra for these robots. There is no second plugin to install.

| CLI selector | Native package |
|---|---|
| `--robot.type=twister` | `lerobot.robots.twister` |
| `--robot.type=bimanual_harvesting` | `lerobot.robots.bimanual_harvesting` |
| `--teleop.type=twister_leader` | `lerobot.teleoperators.twister_leader` |
| `--teleop.type=bimanual_harvesting_leader` | `lerobot.teleoperators.bimanual_harvesting_leader` |

The combined device uses `left_arm_config` for Twister and `right_arm_config` for SO-100.
Ports remain required command arguments. All original motor IDs, rotation modes, limits,
gains, timing settings, camera fields, action names, ordering and calibration IDs remain.
Existing dataset, policy, FPS, display and other command-level options work through the
same LeRobot configurations and loops as the other supported robots.

## Command coverage

| Workflow | Integration |
|---|---|
| `lerobot-setup-motors`, `lerobot-calibrate` | Both followers and leaders, including paired devices |
| `lerobot-teleoperate`, `lerobot-record` | Standard robot/teleop configs, camera and dataset parameters |
| `lerobot-replay` | Standard dataset replay and matching recorded action features |
| `lerobot-rollout` | Standard robot factory, policy/strategy configuration and optional leader |
| `lerobot-train`, dataset tools | Existing feature-driven pipelines; custom 2- or 8-joint datasets use the existing format |
| `lerobot-find-joint-limits` | New types register normally; joint extraction uses ordered action features instead of a single bus |
| Camera/port discovery and information tools | Existing tools and arguments remain unchanged |
| Python and async client configs | Base registries and factories expose the same built-in types without plugin discovery |
| `lerobot-eval` | Remains the existing simulation evaluator; the ZIP does not supply a Twister simulation environment |

Joint-limit kinematics still needs a matching URDF, target frame, joint ordering and
correct mapping of gripper percentage to the model's units. This integration does not
supply or validate those assets. See [POLICIES_AND_SIMULATION.md](POLICIES_AND_SIMULATION.md)
for the preserved simulation conversion helpers and missing simulator work.

## Changes relative to the inputs

- Split the archive's configuration classes across native robot/teleoperator modules;
  their fields, defaults and validation bodies are unchanged.
- Relocated all nine implementation/support modules and adjusted their imports.
- Added built-in registry imports and factory branches for the four hardware types.
  Hardware implementation exports load on demand.
- Selected `time.perf_counter` for the encoder worker's default clock. On the installed
  Windows Python 3.12, `time.monotonic` reports 15.625 ms resolution, whereas
  `perf_counter` reports 100 ns. The old clock caused same-timestamp samples to fault
  the encoder regression test. Tracking thresholds, watchdogs and control logic are unchanged.
- Updated joint-limit observation extraction to use ordered `robot.action_features`,
  allowing a device with multiple buses to pass that step without a `robot.bus` attribute.
- Relocated tests, verifier and documentation and added native CLI regression coverage.
  The offline runner includes explicitly limited NumPy annotation/shape substitutes.

All nine relocated module bodies were compared with the ZIP using Python ASTs and matched,
except for the documented clock selection. All five configuration class ASTs matched exactly.
No file from the original checkout was omitted. Only six pre-existing files were edited:
root README, robot and teleoperator package initializers/factories, and the joint-limit script.
`pyproject.toml`, `uv.lock`, policy code, dataset code, recording/replay/training/rollout loops,
and all original test assets in the destination were preserved.

## Validation performed

- **75 tests passed** using real installed LeRobot dependencies and fake motors/cameras.
  Includes the archive's 71 tests plus fresh-process native registration, real CLI option
  parsing, replay/full rollout config parsing, and multi-bus joint-order coverage.
- **19 documented CLI configurations passed** parsing and disconnected factory construction.
  The verifier parses rollout hardware separately from checkpoint loading. The additional
  integration test also parses a complete rollout configuration using an in-memory ACT config.
- **7 hardware command help checks passed** in fresh processes: setup, calibration,
  teleoperation, recording, replay, rollout and joint limits. Captured Windows help output
  used UTF-8 because upstream help text contains Unicode characters.
- Offline runner: **72 passed, 3 intentionally skipped** because the real-parser tests
  require installed draccus. Offline substitutes do not validate ML or SDK dependencies.
- All Python files under `src` parsed successfully. Copied source and asset contents were audited.

No physical motor/camera connections, real calibration, recording, dataset upload,
training job, policy checkpoint loading, physical rollout or simulator execution was performed.
These tests establish software integration, not physical task performance.

## Provenance

`integration_manifest.json` records the archive hash and source-to-native module mapping.
The original supporting rotation and simulation documentation was retained with updated paths.
`CHANGE_INVENTORY.md` and `VALIDATION.md` are clearly labeled historical reports from the ZIP.
`original_plugin_pyproject.toml` and `LICENSE` preserve the archive's metadata and licensing;
the metadata file is archival and is not a separate install target.

## Subsequent leader torque correction (2026-10-10)

The original AST comparison above describes the initial integration. TwisterLeader.connect()
now explicitly disables torque after startup and verifies both raw Torque_Enable registers;
it refuses connection and cleans up if either motor remains powered. This follows a user
hardware report of both registers reading 1 after connect and 0 after explicit disable.
The startup cause remains unconfirmed. Both rotation modes and combined leaders inherit
the correction without new CLI parameters. All 77 harvesting tests pass with fake hardware;
the patch still requires verification on the hardware computer. See
[USE_CASE_CHANGELOG.md](USE_CASE_CHANGELOG.md) for the six modified files.
