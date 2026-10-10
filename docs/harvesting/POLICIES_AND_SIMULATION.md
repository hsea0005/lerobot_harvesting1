# Policy features and a future LeIsaac model

## Fixed hardware contract

Twister exposes two float position features in this order:

| Index | Feature | Units |
|---|---|---|
| 0 | `rotation.pos` | Cumulative session degrees, default -720..+720 |
| 1 | `gripper.pos` | Calibrated percentage, 0..100 |

The combined embodiment exposes eight, in this order:

| Index | Feature | Units |
|---|---|---|
| 0 | `twister_rotation.pos` | Cumulative session degrees, default -720..+720 |
| 1 | `twister_gripper.pos` | Calibrated percentage, 0..100 |
| 2 | `arm_shoulder_pan.pos` | LeRobot SO-100 joint degrees |
| 3 | `arm_shoulder_lift.pos` | LeRobot SO-100 joint degrees |
| 4 | `arm_elbow_flex.pos` | LeRobot SO-100 joint degrees |
| 5 | `arm_wrist_flex.pos` | LeRobot SO-100 joint degrees |
| 6 | `arm_wrist_roll.pos` | LeRobot SO-100 joint degrees |
| 7 | `arm_gripper.pos` | LeRobot gripper percentage, 0..100 |

The standard feature converter produces `observation.state` and `action` vectors with
dimension 2 or 8 respectively. Record examples add `observation.images.front` as an RGB
image/video. Check `meta/info.json` after recording: its feature names are authoritative.
Do not sort joint names in a simulator or transpose the two groups.

Top-level combined cameras retain their names. Optional cameras under `robot.left_arm_config.cameras`
are prefixed `twister_`; cameras under `robot.right_arm_config.cameras` are prefixed `arm_`. Supply cameras
on only one controller/group for each physical camera device.

## Which policy families can use it

| Family | What the integration supplies | Additional work |
|---|---|---|
| ACT | Standard dataset states, joint position actions, camera frames | Train on the matching two- or eight-joint dataset; documented CLI commands |
| Diffusion | Same dataset contract; no custom robot policy code | Install the diffusion extra and choose observation/action horizon settings |
| SmolVLA | Two/eight dimensions fit the uploaded default padded 32-dimensional limits | Install the extra, fine-tune with images/task text, check checkpoint camera features |
| PI-family VLAs | Generic numerical features can be mapped to the policy inputs | Install extras, fine-tune, and verify padding, action transforms, camera requirements and units |
| GR00T and other specialized policies | Standard dataset is available for their data processors | Configure the custom embodiment/modality mapping and head; robot plugin alone is insufficient |
| RL / simulation policies | Robot API can execute compatible position actions | Provide an environment, observations/rewards/resets and the corresponding policy pipeline |

These are interface-level capabilities, not completed training results. A pretrained
SO-100 checkpoint with six actions cannot directly control the eight-joint combined
robot. A two-joint Twister checkpoint cannot directly control the combined robot either.
Keep cumulative session-position rotation actions unless you deliberately add corresponding transforms to
both training and deployment. For specialized policies, follow their bundled policy
configuration and documentation; do not reinterpret rotation as velocity or gripper as
radians without the same conversion at rollout.

## LeIsaac preparation included now

`src/lerobot/robots/bimanual_harvesting/simulation.py` supplies:

- `TWISTER_ORDER` and `HARVESTING_ORDER` for stable vector ordering.
- `angle_to_sim_radians` and `sim_radians_to_angle`, with explicit orientation at the
  session start and sign.
- `gripper_to_sim_radians`, with explicit physical endpoints.
- `ordered_vector`, which rejects missing/extra features.

These functions are unit-tested, have no Isaac dependency, and preserve cumulative
angles. The fixture is direct drive. For rotation use:

```python
import math
from lerobot.robots.bimanual_harvesting.simulation import angle_to_sim_radians, sim_radians_to_angle

# Read the simulated articulation's physical angle when the session starts.
start_angle = 0.2
joint_target = angle_to_sim_radians(390.0, start_radians=start_angle)
assert math.isclose(joint_target, start_angle + math.radians(390.0))
assert math.isclose(sim_radians_to_angle(joint_target, start_radians=start_angle), 390.0)
```

This maps the session coordinate q to `theta_start + direction * radians(q)`.
Do not wrap 390° to 30°. The simulated rotation joint must represent travel beyond one
revolution, and its observations must retain displacement from the session reference.
If your simulation interface returns wrapped angles, maintain continuous turn tracking
or use a joint state that already preserves the cumulative coordinate.

For an arm joint, supply the assembly reference/sign matching LeRobot's calibrated
SO-100 coordinates rather than applying Twister's session rebase to all joints.
A gripper percentage is not an angle: convert it using measured endpoints and mechanism
geometry. A linear percentage-to-angle mapping may need replacement for a nonlinear jaw
linkage. Preserve the same joint ordering and observation/action units in sim and real data.

## What still has to be built later

This package is **prepared for a custom LeIsaac integration; it is not an already
registered LeIsaac robot or simulation task**. A custom LeRobot Robot class does not
automatically create a LeIsaac articulation or environment.

When fixture geometry is finalized:

1. Export a mechanically correct URDF/USD model with masses, inertias, collision
   geometry, joint axes, direct-drive rotation limits, and gripper linkage.
2. Add an IsaacLab articulation configuration, actuator settings and a scene containing
   the actual SO-100 plus Twister. Use the correct SO-100 geometry; do not assume an SO101
   template is mechanically identical.
3. Create/register the harvesting task and its reset, success, termination and camera
   configuration. LeIsaac's published custom-task tutorial shows the registration workflow.
4. Add a leader/action adapter for `TwisterLeader` / `BimanualHarvestingLeader` or map their
   eight features through a suitable LeIsaac teleoperation device. Its built-in SO101
   teleop device is not an adapter for this fixture by itself.
5. Match camera names, frame ordering, joint units, calibration reference, image timing,
   task text and action semantics to the real dataset. Use the feature order above.
6. Record/export with the LeRobot-format recorder or the converter supported by your
   chosen LeIsaac version. Match dataset format and LeRobot dependencies across your
   simulation and real-hardware environments; keep separate environments if versions differ.
7. Match the fixture's cumulative travel window, session reference, speed cap and reset
   behavior. Preserve multi-turn rotation in joint targets and state; apply no modulo reduction.
8. Validate a short motion-only rollout before training sim-to-real harvesting behavior.

Geometry, inertias, loads and dimensions were not supplied, so an accurate fixture
URDF/USD cannot be fabricated from the two motor names. No dummy mesh or fictional
dynamic parameters are included. This does not block collecting your real dataset now.

Official references:

- https://lightwheelai.github.io/leisaac/docs/tutorials/custom_task/
- https://lightwheelai.github.io/leisaac/docs/features/lerobot_recorder/
- https://github.com/LightwheelAI/leisaac
