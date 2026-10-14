# Harvesting use-case change log

Date: 2026-10-10 

Fork: https://github.com/hsea0005/lerobot_harvesting1.git

Upstream: https://github.com/huggingface/lerobot.git

Checkout: `D:\FYP_HS\lerobotharvesting1\lerobot_harvesting1`

## Fork baseline

The local merge-base with upstream/main is `b9cb121cb7d4e3e26ec5c906d08dda68d151ba52`.
The custom integration is committed as `fed65dd2eb0092c5d7af672c07f99cfde16ec403` (initial framework).
This inventory uses that Git comparison plus this request's working-tree additions.
Creating the fork itself does not change tracked source. Its creation date is not assumed.

## 2026-10-10: native custom hardware integration

- Copied the existing lerobot checkout to lerobot1 and assimilated LeRobot_Twister_v1 (1).zip.
- Relocated Twister and Twister + SO-100 followers/leaders into native robot/teleoperator folders.
- Registered four native hardware types and adapted factories; existing CLI parameters were retained.
- Preserved original configuration fields/defaults/validation and control logic; selected the
  high-resolution perf_counter clock for the worker on Windows Python 3.12.
- Changed joint-limit extraction to ordered action features for multiple buses.
- Transferred only that integration to this fork, preserving destination Git metadata and unrelated files.
- Original integration: **40 files, comprising 34 added and 6 modified**.
- Validation in this destination: 75 hardware-free tests and 19 documented CLI examples passed.
  Seven hardware help checks were also performed during the original integration. No real hardware
  operation, dataset upload, training job or physical inference was run by those checks.

Source archive SHA-256: `41d5c12a4007f90e698d785937f28c9b867ae295aea286219c0b1f34bb401197`.
See [INTEGRATION.md](INTEGRATION.md) for boundaries and [integration_manifest.json](integration_manifest.json)
for source-to-native mappings. Historical bundle reports are labeled as historical.

## 2026-10-10: separate device workflows

Added training_device.ipynb and hardware_device.ipynb as adaptations of quickstart.ipynb.
The original quickstart notebook remains unchanged. Both generate PowerShell terminal commands only;
Run All does not execute installations, jobs, uploads or hardware operations. Both support standalone
Twister and combined Twister + SO-100. The environments are harvesting_train and harvesting_hardware,
created locally on their respective computers. Shared code does not share environments or calibration.

The training notebook includes the conditional repair for the diagnosed RTX 4080 SUPER/driver 561.03:
CUDA 12.6 PyTorch 2.8.0, torchvision 0.23.0 and TorchCodec 0.7.0. Hardware inference defaults to CPU.
Datasets/models can be transferred through the Hub or copied completely between computers.

This request adds **3 files** (two notebooks and this log) and modifies **2 existing files**:
README.md in this documentation folder and integration_manifest.json gain notebook links/provenance.

## Complete inventory versus fork baseline

**45 files: 38 added and 7 modified.** The two documentation edits above affect files already added
by the integration, so they retain Added status in this upstream comparison. All paths are relative
to the repo root and each row links to the file.

| Status | File | Purpose / change |
|---|---|---|
| Modified | [README.md](../../README.md) | Links custom robot setup and integration documentation. |
| Added | [docs/harvesting/CHANGE_INVENTORY.md](../../docs/harvesting/CHANGE_INVENTORY.md) | Labeled historical inventory from the supplied ZIP. |
| Added | [docs/harvesting/INTEGRATION.md](../../docs/harvesting/INTEGRATION.md) | Layout, transfer provenance, command coverage and limits. |
| Added | [docs/harvesting/LICENSE](../../docs/harvesting/LICENSE) | License retained from the custom bundle. |
| Added | [docs/harvesting/POLICIES_AND_SIMULATION.md](../../docs/harvesting/POLICIES_AND_SIMULATION.md) | Data/policy contracts and future simulation conversions. |
| Added | [docs/harvesting/README.md](../../docs/harvesting/README.md) | Hardware/workflow commands; links device notebooks and this log. |
| Added | [docs/harvesting/ROTATION.md](../../docs/harvesting/ROTATION.md) | Rotation behavior, controller parameters and recovery. |
| Added | [docs/harvesting/USE_CASE_CHANGELOG.md](../../docs/harvesting/USE_CASE_CHANGELOG.md) | This dated log and complete file inventory. |
| Added | [docs/harvesting/VALIDATION.md](../../docs/harvesting/VALIDATION.md) | Labeled historical standalone bundle validation report. |
| Added | [docs/harvesting/integration_manifest.json](../../docs/harvesting/integration_manifest.json) | Archive hash, file mapping, validation and notebook provenance. |
| Added | [docs/harvesting/original_plugin_pyproject.toml](../../docs/harvesting/original_plugin_pyproject.toml) | Archived plugin metadata; not an install target. |
| Added | [examples/harvesting/verify_install.py](../../examples/harvesting/verify_install.py) | Real CLI parsing/factory checks without hardware connection. |
| Added | [examples/notebooks/hardware_device.ipynb](../../examples/notebooks/hardware_device.ipynb) | Hardware setup, calibration, recording/replay and deployment. |
| Added | [examples/notebooks/training_device.ipynb](../../examples/notebooks/training_device.ipynb) | Training setup, CUDA checks/repair, ACT training/resume and handoff. |
| Modified | [src/lerobot/cameras/opencv/camera_opencv.py](../../src/lerobot/cameras/opencv/camera_opencv.py) | Select capture format before FPS; avoid redundant DirectShow stream resets. |
| Added | [tests/cameras/test_opencv_capture_settings.py](../../tests/cameras/test_opencv_capture_settings.py) | Hardware-free capture negotiation, fallback, validation and cleanup regressions. |
| Modified | [src/lerobot/robots/__init__.py](../../src/lerobot/robots/__init__.py) | Registers native custom follower configurations. |
| Added | [src/lerobot/robots/bimanual_harvesting/__init__.py](../../src/lerobot/robots/bimanual_harvesting/__init__.py) | Exports native configurations and hardware implementation classes. |
| Added | [src/lerobot/robots/bimanual_harvesting/bimanual_harvesting.py](../../src/lerobot/robots/bimanual_harvesting/bimanual_harvesting.py) | Combined eight-joint follower and camera/action routing. |
| Added | [src/lerobot/robots/bimanual_harvesting/config_bimanual_harvesting.py](../../src/lerobot/robots/bimanual_harvesting/config_bimanual_harvesting.py) | Twister left/SO-100 right follower configuration. |
| Added | [src/lerobot/robots/bimanual_harvesting/pair.py](../../src/lerobot/robots/bimanual_harvesting/pair.py) | Shared paired-device connection/cleanup and action splitting. |
| Added | [src/lerobot/robots/bimanual_harvesting/simulation.py](../../src/lerobot/robots/bimanual_harvesting/simulation.py) | Joint order/unit conversions; no complete simulation environment. |
| Added | [src/lerobot/robots/twister/__init__.py](../../src/lerobot/robots/twister/__init__.py) | Exports native configurations and hardware implementation classes. |
| Added | [src/lerobot/robots/twister/config_twister.py](../../src/lerobot/robots/twister/config_twister.py) | Twister hardware/follower fields, defaults and validation. |
| Added | [src/lerobot/robots/twister/continuous.py](../../src/lerobot/robots/twister/continuous.py) | Feedback/control worker and watchdog; perf_counter clock on Windows. |
| Added | [src/lerobot/robots/twister/control.py](../../src/lerobot/robots/twister/control.py) | Conversions, encoder unwrapping, motion guards and controller. |
| Added | [src/lerobot/robots/twister/device.py](../../src/lerobot/robots/twister/device.py) | Shared Feetech setup, calibration and resource lifecycle. |
| Added | [src/lerobot/robots/twister/twister.py](../../src/lerobot/robots/twister/twister.py) | Two-joint follower and optional cameras. |
| Modified | [src/lerobot/robots/utils.py](../../src/lerobot/robots/utils.py) | Constructs Twister and bimanual followers in the native factory. |
| Modified | [src/lerobot/scripts/lerobot_find_joint_limits.py](../../src/lerobot/scripts/lerobot_find_joint_limits.py) | Reads ordered action features rather than assuming one bus. |
| Modified | [src/lerobot/teleoperators/__init__.py](../../src/lerobot/teleoperators/__init__.py) | Registers corresponding native leader configurations. |
| Added | [src/lerobot/teleoperators/bimanual_harvesting_leader/__init__.py](../../src/lerobot/teleoperators/bimanual_harvesting_leader/__init__.py) | Exports native configurations and hardware implementation classes. |
| Added | [src/lerobot/teleoperators/bimanual_harvesting_leader/bimanual_harvesting_leader.py](../../src/lerobot/teleoperators/bimanual_harvesting_leader/bimanual_harvesting_leader.py) | Combined leader routing and torque control. |
| Added | [src/lerobot/teleoperators/bimanual_harvesting_leader/config_bimanual_harvesting_leader.py](../../src/lerobot/teleoperators/bimanual_harvesting_leader/config_bimanual_harvesting_leader.py) | Combined leader configuration. |
| Added | [src/lerobot/teleoperators/twister_leader/__init__.py](../../src/lerobot/teleoperators/twister_leader/__init__.py) | Exports native configurations and hardware implementation classes. |
| Added | [src/lerobot/teleoperators/twister_leader/config_twister_leader.py](../../src/lerobot/teleoperators/twister_leader/config_twister_leader.py) | Native standalone leader configuration. |
| Added | [src/lerobot/teleoperators/twister_leader/twister_leader.py](../../src/lerobot/teleoperators/twister_leader/twister_leader.py) | Passive leader actions, feedback and torque handling. |
| Modified | [src/lerobot/teleoperators/utils.py](../../src/lerobot/teleoperators/utils.py) | Constructs custom leaders in the native factory. |
| Added | [tests/robots/harvesting/fakes.py](../../tests/robots/harvesting/fakes.py) | Fake motor bus/cameras for regression tests. |
| Added | [tests/robots/harvesting/offline_bootstrap.py](../../tests/robots/harvesting/offline_bootstrap.py) | Limited external-import and array-shape substitutes for offline tests. |
| Added | [tests/robots/harvesting/run_offline.py](../../tests/robots/harvesting/run_offline.py) | Offline tests against the relocated native source. |
| Added | [tests/robots/harvesting/test_continuous.py](../../tests/robots/harvesting/test_continuous.py) | Tracking, watchdog and worker lifecycle regressions. |
| Added | [tests/robots/harvesting/test_harvesting.py](../../tests/robots/harvesting/test_harvesting.py) | Hardware config, conversions, lifecycle and routing tests. |
| Added | [tests/robots/harvesting/test_native_integration.py](../../tests/robots/harvesting/test_native_integration.py) | Native registry, CLI config and multi-bus joint-order checks. |
| Added | [tests/robots/harvesting/test_source_contract.py](../../tests/robots/harvesting/test_source_contract.py) | CLI/config naming and dataset feature contracts. |

## Notebook validation

All code cells in both notebooks were executed as command generators for both embodiments.
22 generated CLI configurations parsed with the real LeRobot/draccus configurations. Resume
commands were checked without loading absent checkpoint files. Rollout parsing substituted an
in-memory ACT configuration for the not-yet-trained model path; no remote model was downloaded.
The original quickstart hash was unchanged and all inventory links resolved. Notebook outputs
and execution counts remain cleared. No installations, jobs, uploads or hardware operations ran.

## Environment operations outside the source inventory

The user created harvesting_train with Python 3.12, installed .[training], and installed FFmpeg via
conda-forge. CPU-only PyTorch was diagnosed and repair commands were supplied. Completion of that
repair or training is not claimed here. Conda environments, credentials, Hugging Face caches,
calibration files, generated datasets and model checkpoints are runtime artifacts, not source edits.
This work does not change pyproject.toml, uv.lock or the original quickstart.ipynb.

## Maintain this log

Append a dated entry for future use-case file changes and reconcile the inventory against the baseline
commit plus untracked files. Keep runtime artifacts and unrelated upstream changes out of this list.

## 2026-10-10: verify passive Twister leader after connection

User diagnostics on hardware reported Torque_Enable=1 for both leader motors after
connect(), with is_follower=False. Explicit disable_torque() changed both to zero.
The startup operation responsible for enabling torque has not been established.

- Modified src/lerobot/teleoperators/twister_leader/twister_leader.py: disable torque
  after shared startup and verify both raw Torque_Enable registers. Refuse connection
  and clean up on a powered motor or read failure. Applies to standalone and combined
  leaders, with existing CLI fields and follower startup unchanged.
- Modified tests/robots/harvesting/fakes.py: model torque state and raw torque-register reads.
- Modified tests/robots/harvesting/test_harvesting.py: regressions for torque left enabled
  after startup and refusal/cleanup when either motor reports enabled, in both rotation modes.
- Updated docs/harvesting/INTEGRATION.md, docs/harvesting/integration_manifest.json and
  this changelog to record the adjustment: six existing files modified, no new files.

Validation: both new regressions failed before the fix; all 77 harvesting tests passed
afterwards with real dependencies and fake motors/cameras. The patched connection still
needs verification on the hardware computer. Sync the changed source and start a fresh
process; an existing editable installation needs no dependency reinstallation.
Gripper startup alignment/direction remains a separate check after passive operation.

## 2026-10-14: Windows three-camera capture negotiation

The user resolved a hub-related black-camera problem, then recording still failed in
OpenCV 4.13 DirectShow while setting a camera's height or FPS. The existing Windows
configuration applied FOURCC only after FPS, so requesting MJPG did not select it
before the failing FPS operation. The precise driver/USB cause remains unconfirmed.

- Modified src/lerobot/cameras/opencv/camera_opencv.py: select FOURCC first; recheck it
  after dimensions and after FPS on Windows. Avoid resetting already matching size,
  FPS and FOURCC on Windows DirectShow. Preserve dimension/FPS validation, fallback
  warnings and failure cleanup. No public CLI fields or default values changed.
- Added tests/cameras/test_opencv_capture_settings.py: nine regressions using real
  OpenCV/LeRobot imports and fake capture handles. Covers format-dependent FPS
  failure, redundant-setter failure, resize/FPS format resets, unspecified/rejected
  formats, rejected FPS, non-Windows setup and connection cleanup.
- Updated README.md and INTEGRATION.md in this folder, this changelog and
  integration_manifest.json. One new file and five existing files changed.

Validation: three targeted regressions failed before the patch. All nine new camera
tests and all 77 harvesting tests passed afterward without physical camera/motor
connections. Existing pytest-based image-fixture camera tests were not run because
pytest is not installed in the validation environment. The corrected setup still
requires verification with all three cameras on the hardware computer. Sync the
changed camera_opencv.py and start a new process; no dependency reinstall is needed.
