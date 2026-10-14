# LeRobot Twister v1.2.0

A direct-drive two-joint STS3215 fixture and a fixture + SO-100 embodiment for the uploaded
LeRobot **0.6.2 / Python 3.12+** source. The custom hardware is integrated directly into this `lerobot_harvesting1` checkout as native
Robot and Teleoperator implementations; no separate plugin installation is required.

Use the normal `lerobot-*` executables and their CLI arguments. No example configuration
files are required or supplied. Serial ports are required CLI arguments, with no COM-port
defaults in the plugin. Motor IDs, device IDs, controller settings, cameras, dataset options
and training/deployment settings can all be passed on the command line.

| Hardware | Type | Your current port |
|---|---|---|
| Right SO-100 leader | `teleop.type=so100_leader` | COM13 |
| Twister leader | `teleop.type=twister_leader` | COM14 |
| Right SO-100 follower | `robot.type=so100_follower` | COM15 |
| Twister follower | `robot.type=twister` | COM16 |

For `bimanual_harvesting` and `bimanual_harvesting_leader`, **left = Twister, right = SO-100**.
Their CLI follows the uploaded native bimanual configuration: `left_arm_config.port` and
`right_arm_config.port`. The port assignments above are examples in these commands, not
fixed values in the implementation. Change them directly in your command if needed.

## Install or update

Open PowerShell in `D:\FYP_HS\lerobotharvesting1\lerobot_harvesting1`. Use a dedicated environment so the original
checkout can keep its existing installation:

```powershell
conda create -n lerobot1 python=3.12 -y
conda activate lerobot1
$env:PYTHONUTF8 = "1"
python -m pip install -e ".[core_scripts,training,feetech]"
python examples/harvesting/verify_install.py
```

The folder is named `lerobot_harvesting1`; the Python package and executable names remain `lerobot`
and `lerobot-*`. CUDA/PyTorch and FFmpeg/PyAV must match your PC. The examples below
use CUDA and PyAV. See [INTEGRATION.md](INTEGRATION.md) for the layout and command coverage.

To inspect available hardware options:

```powershell
lerobot-teleoperate --robot.type=twister --teleop.type=twister_leader --help
lerobot-teleoperate --robot.type=bimanual_harvesting --teleop.type=bimanual_harvesting_leader --help
```

PowerShell uses the backtick at the end of a line to continue a command. Leave no spaces
after that backtick. You may also place every argument on one line. None of these commands
needs `python -m` before the `lerobot-*` executable.

## Motor ID setup

The default Twister IDs are rotation 1 and gripper 2. The usual SO-100 IDs are 1..6.
Each controller is a separate bus, so IDs can repeat across controllers. Connect only the
motor requested by the setup prompt; power the servos off before changing the wiring.
Provide both servo power and USB communication. The Twister prompt identifies the device
and asks for gripper first, then rotation. During ordinary operation daisy-chain rotation
and gripper on their controller.

```powershell
lerobot-setup-motors --teleop.type=twister_leader --teleop.port=COM14 --teleop.id=harvesting_leader_twister
lerobot-setup-motors --robot.type=twister --robot.port=COM16 --robot.id=harvesting_follower_twister
```

If your SO-100 devices already have the correct standard IDs, skip their ID setup.
Otherwise use the normal native commands:

```powershell
lerobot-setup-motors --teleop.type=so100_leader --teleop.port=COM13 --teleop.id=harvesting_leader_arm
lerobot-setup-motors --robot.type=so100_follower --robot.port=COM15 --robot.id=harvesting_follower_arm
```

For custom Twister motor IDs, add `--robot.rotation_motor_id=...` and
`--robot.gripper_motor_id=...`, or their `--teleop.*` equivalents. Use the same IDs for setup,
calibration and subsequent operation. These flags change the IDs written by motor setup;
changing only a later teleoperation flag does not rename a motor in EEPROM.

## Calibration

Calibrate the four devices using your chosen IDs. The example IDs match the preceding
package so existing calibration files can be reused despite the changed COM assignments.

```powershell
lerobot-calibrate --teleop.type=so100_leader --teleop.port=COM13 --teleop.id=harvesting_leader_arm
lerobot-calibrate --teleop.type=twister_leader --teleop.port=COM14 --teleop.id=harvesting_leader_twister
lerobot-calibrate --robot.type=so100_follower --robot.port=COM15 --robot.id=harvesting_follower_arm
lerobot-calibrate --robot.type=twister --robot.port=COM16 --robot.id=harvesting_follower_twister
```

You can instead calibrate the pair through its native CLI interface:

```powershell
lerobot-calibrate `
  --teleop.type=bimanual_harvesting_leader `
  --teleop.left_arm_config.port=COM14 `
  --teleop.right_arm_config.port=COM13 `
  --teleop.id=harvesting_leader

lerobot-calibrate `
  --robot.type=bimanual_harvesting `
  --robot.left_arm_config.port=COM16 `
  --robot.right_arm_config.port=COM15 `
  --robot.id=harvesting_follower
```

The pair derives child IDs as `<id>_twister` and `<id>_arm`, keeping compatibility with
existing calibration files. Changing your top-level ID selects a different calibration
identity; keep the chosen IDs consistent through calibration, teleoperation, recording
and rollout. Ports are independent of calibration identity. Standard LeRobot saves its
calibration results as JSON internally; you do not edit those files to set runtime parameters.

Twister calibration asks you to center and move **only the gripper** through safe travel.
Its endpoints must not cross the encoder seam. Rotation has a full 0..4095 raw range and
requires no home movement. Set `--robot.gripper_inverted=true` (or the leader equivalent)
before calibration if you need inverted gripper percentage. Leave `rotation_homing_offset`
unchanged after calibration. Reuse saved calibration with ENTER, or choose `c` to recalibrate.

## Teleoperation

Twister only:

```powershell
lerobot-teleoperate `
  --robot.type=twister `
  --robot.port=COM16 `
  --robot.id=harvesting_follower_twister `
  --teleop.type=twister_leader `
  --teleop.port=COM14 `
  --teleop.id=harvesting_leader_twister `
  --fps=30
```

Twister plus the right SO-100:

```powershell
lerobot-teleoperate `
  --robot.type=bimanual_harvesting `
  --robot.left_arm_config.port=COM16 `
  --robot.right_arm_config.port=COM15 `
  --robot.id=harvesting_follower `
  --teleop.type=bimanual_harvesting_leader `
  --teleop.left_arm_config.port=COM14 `
  --teleop.right_arm_config.port=COM13 `
  --teleop.id=harvesting_leader `
  --fps=30
```

Start the leader/follower in corresponding task poses and keep them still during connection.
Rotation starts at logical zero independently on each fixture, then follows cumulative
leader displacement. Alignment at 200° followed by an additional 190° has target **390°**.
The direct-drive fixture tracks the encoder seam in both directions. Rotation uses velocity
mode internally with a software position controller; LeRobot actions remain position targets.
Gripper actions remain calibrated percentage. No physical rotation home is commanded.

The ordinary leader is passive. The pair presents one eight-joint action frame, with
sequential serial writes to its two controllers. Demonstrations define the alignment,
twisting and arm coordination; the plugin does not impose a sequence of task stages.
Ctrl+C ends teleoperation.

## Change settings directly on the CLI

Defaults provide a cumulative travel window -720°..+720°, raw rotation speed cap 400,
50 Hz feedback/control, 0.5° position tolerance and a 1 s fresh-action timeout.
Restrict the travel window to what your mechanism and cabling permit. For example:

```powershell
lerobot-teleoperate `
  --robot.type=twister --robot.port=COM16 --robot.id=harvesting_follower_twister `
  --robot.rotation_speed=300 --robot.rotation_kp=1.5 `
  --robot.rotation_min_deg=-450 --robot.rotation_max_deg=450 `
  --robot.rotation_motor_id=1 --robot.gripper_motor_id=2 `
  --teleop.type=twister_leader --teleop.port=COM14 --teleop.id=harvesting_leader_twister `
  --teleop.rotation_min_deg=-450 --teleop.rotation_max_deg=450
```

For the pair use the same settings under `--robot.left_arm_config.*` or
`--teleop.left_arm_config.*`. SO-100 settings belong to `--robot.right_arm_config.*` or
`--teleop.right_arm_config.*`. For example, add
`--robot.left_arm_config.rotation_speed=300` to the combined command. Each option has a
native dataclass default where appropriate; ports are always supplied. Nothing loads a
preset file at device startup. See `ROTATION.md` for controller parameters and recovery.

Bench-check slow forward/reverse motion, the 359°→361° seam crossing, 200°→390°, return to
the starting pose and stop behavior before recording on an object. Real physical overshoot
and load behavior remain unverified. An encoder sampling gap over 0.15 s or implausible
motion faults tracking. Turn count resets at reconnection, and remains fixed across episodes
within a connection. No fresh actions for 1 s causes rotation to stop until commands resume.
A host crash or unreachable serial bus can leave the last velocity command active; keep
servo power readily disconnectable during testing and operation.

## Record and upload datasets

Find the camera index using the native tool:

```powershell
lerobot-find-cameras opencv
hf auth login
```

For uploading, log in with write access. Replace `YOUR_HF_USERNAME` in the commands with
your real username. Camera index 0 below is an example; pass your actual camera on the CLI.
Start with two short episodes, then change `--dataset.num_episodes` to collect more.

Twister only:

```powershell
lerobot-record `
  --robot.type=twister --robot.port=COM16 --robot.id=harvesting_follower_twister `
  --robot.cameras="{front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}" `
  --teleop.type=twister_leader --teleop.port=COM14 --teleop.id=harvesting_leader_twister `
  --dataset.repo_id=YOUR_HF_USERNAME/twister_demo `
  --dataset.single_task="Align the object, assist with the gripper, then twist further." `
  --dataset.fps=30 --dataset.num_episodes=2 `
  --dataset.episode_time_s=30 --dataset.reset_time_s=15 `
  --dataset.no_stamp=true --dataset.push_to_hub=true `
  --display_data=false --play_sounds=false
```

Twister plus SO-100:

```powershell
lerobot-record `
  --robot.type=bimanual_harvesting `
  --robot.left_arm_config.port=COM16 --robot.right_arm_config.port=COM15 `
  --robot.id=harvesting_follower `
  --robot.cameras="{front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}" `
  --teleop.type=bimanual_harvesting_leader `
  --teleop.left_arm_config.port=COM14 --teleop.right_arm_config.port=COM13 `
  --teleop.id=harvesting_leader `
  --dataset.repo_id=YOUR_HF_USERNAME/bimanual_harvesting_demo `
  --dataset.single_task="Align the object, assist with the gripper, then harvest." `
  --dataset.fps=30 --dataset.num_episodes=2 `
  --dataset.episode_time_s=30 --dataset.reset_time_s=15 `
  --dataset.no_stamp=true --dataset.push_to_hub=true `
  --display_data=false --play_sounds=false
```

Uploading occurs on exit after saved episodes are finalized. Add `--dataset.private=true`
for a newly created private repository, or set `--dataset.push_to_hub=false` for local-only
recording. `no_stamp=true` keeps the chosen repository name, so use that same name for
training. Use a new repo ID for a fresh dataset; append to a compatible dataset explicitly
with `--resume=true`. Record and rollout must use matching camera names and dimensions.

Keep the physical starting arrangement consistent across connections. The sampling worker
runs throughout resets, so return the leader/follower toward the session reference as
appropriate without reconnecting between stages. Native recording stores the requested
leader action before robot-side clipping. The default `max_relative_target` remains null;
the speed cap controls rotation speed. Move the leader slowly enough for good following.

The v1.2 CLI change preserves v1.1 joint names, position units and calibration IDs; compatible
v1.1 recordings/checkpoints can still be used. V1.0 bounded-encoder recordings/checkpoints
have different rotation semantics and must not be mixed with cumulative data.

## Replay a recorded episode

Use the same physical session reference and motion settings as recording.

```powershell
lerobot-replay `
  --robot.type=twister --robot.port=COM16 --robot.id=harvesting_follower_twister `
  --dataset.repo_id=YOUR_HF_USERNAME/twister_demo --dataset.episode=0 --play_sounds=false

lerobot-replay `
  --robot.type=bimanual_harvesting `
  --robot.left_arm_config.port=COM16 --robot.right_arm_config.port=COM15 `
  --robot.id=harvesting_follower `
  --dataset.repo_id=YOUR_HF_USERNAME/bimanual_harvesting_demo --dataset.episode=0 --play_sounds=false
```

## Train

ACT infers state/action dimensions and image features from the matching dataset.
Use the command for the embodiment you recorded:

```powershell
lerobot-train `
  --dataset.repo_id=YOUR_HF_USERNAME/twister_demo --dataset.video_backend=pyav `
  --policy.type=act --policy.device=cuda --policy.push_to_hub=false `
  --output_dir=outputs/train/twister_act --job_name=twister_act `
  --batch_size=8 --steps=20000 --env_eval_freq=0 --wandb.enable=false

lerobot-train `
  --dataset.repo_id=YOUR_HF_USERNAME/bimanual_harvesting_demo --dataset.video_backend=pyav `
  --policy.type=act --policy.device=cuda --policy.push_to_hub=false `
  --output_dir=outputs/train/bimanual_harvesting_act --job_name=bimanual_harvesting_act `
  --batch_size=8 --steps=20000 --env_eval_freq=0 --wandb.enable=false
```

These are starting experiment settings, not measured success-rate guarantees. Training does
not connect motors and needs no serial ports. Follow policy-specific extras and input
requirements for other imitation-learning models. For example, fine-tune SmolVLA:

```powershell
pip install -e ".[smolvla]"
lerobot-train `
  --policy.path=lerobot/smolvla_base --policy.device=cuda --policy.push_to_hub=false `
  --dataset.repo_id=YOUR_HF_USERNAME/bimanual_harvesting_demo --dataset.video_backend=pyav `
  --output_dir=outputs/train/harvesting_smolvla --job_name=harvesting_smolvla `
  --batch_size=4 --steps=20000 --env_eval_freq=0 --wandb.enable=false
```

## Rollout

The uploaded LeRobot version deploys with `lerobot-rollout`. Pass the trained checkpoint
path and the follower ports directly; no leader is required for ordinary autonomous rollout.

```powershell
lerobot-rollout `
  --robot.type=twister --robot.port=COM16 --robot.id=harvesting_follower_twister `
  --robot.cameras="{front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}" `
  --policy.path=outputs/train/twister_act/checkpoints/last/pretrained_model `
  --strategy.type=base --fps=30 --duration=30 `
  --task="Align the object, assist with the gripper, then twist further." `
  --return_to_initial_position=false --display_data=false --play_sounds=false

lerobot-rollout `
  --robot.type=bimanual_harvesting `
  --robot.left_arm_config.port=COM16 --robot.right_arm_config.port=COM15 `
  --robot.id=harvesting_follower `
  --robot.cameras="{front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}" `
  --policy.path=outputs/train/bimanual_harvesting_act/checkpoints/last/pretrained_model `
  --strategy.type=base --fps=30 --duration=30 `
  --task="Align the object, assist with the gripper, then harvest." `
  --return_to_initial_position=false --display_data=false --play_sounds=false
```

Match motion settings, the task starting arrangement and camera configuration to recording.
The example disables automatic return to the initial pose; normal teardown stops rotation
and disables torque. Check held-out episodes and short unloaded physical rollouts before
expanding the task. See `POLICIES_AND_SIMULATION.md` for the future LeIsaac contract.

## Checks and included files

- `src/lerobot/robots/twister/` and `src/lerobot/robots/bimanual_harvesting/`: followers and shared control.
- `src/lerobot/teleoperators/twister_leader/` and `src/lerobot/teleoperators/bimanual_harvesting_leader/`: leaders.
- `examples/harvesting/verify_install.py`: real CLI parsing and factory checks without motor connections.
- `tests/robots/harvesting/`: hardware-free regression tests imported from the ZIP.
- `docs/harvesting/`: original supporting documents and integration notes.

Run from the repository root after installing this checkout:

```powershell
python examples/harvesting/verify_install.py
python -m unittest discover -s tests/robots/harvesting -v
```

`python tests/robots/harvesting/run_offline.py` supplies external-import substitutes
when dependencies are unavailable. See `INTEGRATION.md` for the integration validation;
`VALIDATION.md` preserves the original bundle's validation report.

Official references:

- https://huggingface.co/docs/lerobot/main/en/integrate_hardware
- https://huggingface.co/docs/lerobot/main/en/so100
- https://wiki.seeedstudio.com/lerobot_so100m_new/
- https://files.seeedstudio.com/products/Feetech/108090023_STS3215-C001_Datasheet.pdf
- https://lightwheelai.github.io/leisaac/docs/tutorials/custom_task/

## Separate training and hardware computers

Use [training_device.ipynb](../../examples/notebooks/training_device.ipynb) on the training
computer and [hardware_device.ipynb](../../examples/notebooks/hardware_device.ipynb) on
the computer connected to controllers and cameras. Edit Configuration and Run All to
generate PowerShell commands, then paste selected commands into a terminal. The notebooks
do not execute installations, hardware operations or jobs. Both support Twister-only and
Twister + SO-100. Create separate local Conda environments and match the dataset/model IDs
and code commit across both computers.

[USE_CASE_CHANGELOG.md](USE_CASE_CHANGELOG.md) records the file changes since the fork baseline.

## Windows three-camera capture troubleshooting

For the wrist/front/top arrangement, retain consistent camera names, image dimensions
and dataset FPS across recording, training and deployment. Windows indices can change
when USB connections change. Test all three cameras simultaneously; discovery opens
them sequentially. Spread cameras across working USB connections; the user observed
black/failing cameras with all three on one hub.

Camera entries can request backend: DSHOW and fourcc: MJPG when the device supports
that format. Discovery reports the default FOURCC, not all supported formats. Requested
MJPG can fall back with a warning; it is not a guarantee of compressed USB capture.

The 2026-10-14 patch in src/lerobot/cameras/opencv/camera_opencv.py selects FOURCC
before size/FPS negotiation, rechecks it after Windows changes, and avoids redundant
DirectShow property writes. This addresses the configuration order exposed by the
reported pVih assertion; it does not guarantee that a driver or shared USB connection
can support the requested simultaneous streams. Requested size/FPS validation remains.

Sync that source file to the hardware repository before retrying. A failed new recording
may already have created dataset metadata: use --resume=true with the same compatible
ID/root, or choose a fresh dataset ID/root. Names such as side and top are different
dataset features and cannot be interchanged when resuming. With display_data=false,
Foxglove streaming is disabled even when display_mode=foxglove is supplied.
