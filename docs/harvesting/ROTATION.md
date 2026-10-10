# Direct-drive cumulative rotation

## Coordinates and your task sequence

The default `rotation_control="continuous"` exposes `rotation.pos` as cumulative motor-shaft
**degrees from the connection starting pose**. Motor motion and fixture motion have the same
angular displacement. The gripper feature, `gripper.pos`, is calibrated travel percentage,
0..100. In the combined robot the names become `twister_rotation.pos` and
`twister_gripper.pos`.

| Stage | Rotation target | Displacement since previous stage |
|---|---|---|
| Connection, any physical starting angle | 0° | Establish reference only |
| Align the object | 200° | +200° |
| Twist after alignment | 390° | +190° |
| Return to session starting angle | 0° | -390° |

An encoder sequence of 350°, 359°, 0°, 15° is tracked as 350°, 359°, 360°, 375° when the
starting reference is at encoder zero. Crossing backward also works. If the starting
encoder reading is 247°, that reading becomes logical zero; subsequent displacement of
390° becomes `rotation.pos=390`, irrespective of the seam location. A 390° target is never
converted to a 30° position command. There is no rebase between alignment and twisting.

## Servo modes and controller

The STS3215 has a single-turn raw encoder reading here: 0..4095, with 4096 counts per
revolution. The uploaded Feetech `configure_motors()` selects that feedback format by
clearing Phase bit 4. Unwrapping feedback alone would not make a bounded Goal_Position
command execute an extra revolution.

For continuous mode this plugin uses:

- Rotation: STS3215 `Operating_Mode=1` (velocity), plus a 50 Hz software position loop.
- Gripper: `Operating_Mode=0` (position), with its usual calibrated range.
- Leader rotation: velocity mode, torque disabled, continuously sampled for turn tracking.

The public Robot/Teleoperator features are still **position actions**. The follower
computes cumulative position error, converts it to a signed raw Goal_Velocity command,
and caps its magnitude. Near the target, the proportional gain reduces speed; inside the
0.5° tolerance it commands zero. Position error after an overshoot commands correction in
the opposite direction. This is not a measured guarantee of overshoot-free physical motion;
load, friction, acceleration and speed-loop behavior need bench validation.

Feetech documents closed-loop speed mode, relative stepping and a separate multi-loop
position mode in its STS3215 datasheet. This implementation uses velocity mode rather
than relying on the servo's finite multi-loop position range or its power-loss behavior:
https://files.seeedstudio.com/products/Feetech/108090023_STS3215-C001_Datasheet.pdf
The vendor Python SDK also supplies WheelMode and signed speed writes:
https://gitee.com/ftservo/FTServo_Python/blob/main/scservo_sdk/sms_sts.py

Speed commands use the raw encoder-counts-per-second convention used by the uploaded
LeRobot LeKiwi implementation: `raw_speed = degrees_per_second * 4096 / 360`. The default
raw cap 400 corresponds to about 35.16°/s under that convention. Validate actual shaft
speed and sign on your exact servo firmware. `rotation_velocity_sign=-1` reverses the
control output if a positive raw command reduces the reported encoder angle. It does
not reverse the meaning of the observed cumulative angle.

## Starting pose, episodes and deployment

No rotation home movement is commanded. Before enabling follower torque the plugin sends
rotation speed zero and seeds only the gripper's current position. The first tracked
rotation sample defines zero independently on leader and follower. Keep both still while
connecting and place them in corresponding task poses. Teleoperation reproduces the
leader's displacement; it does not automatically correct a different physical starting
orientation between leader and follower.

The reference lasts for the **connection**, not one episode. The sampling worker remains
active while the recorder waits, during resets, during camera reads and between alignment
and twisting. Return toward the session reference by moving the leader during reset if
appropriate. Do not restart the device midway through a demonstration to erase turns.

Reconnecting defines a new zero and discards the turn count. Before a new recording or
rollout session, establish the task starting arrangement used for your training data.
Starting from a new physical orientation changes what a given cumulative target means.
Camera observations can help a trained policy adapt only if corresponding situations are
represented in the data; the coordinate choice alone does not guarantee that adaptation.

Version 1.1 uses a different rotation coordinate from version 1.0's bounded encoder
position. Use a fresh dataset and retrain rather than mixing their actions or checkpoints.

## Sampling assumptions and stops

The tracker selects the shortest signed encoder displacement between consecutive samples.
It is valid only if actual movement stays below half a revolution between samples and
within the configured speed bound. It cannot identify an unobserved whole revolution.
Defaults are 50 Hz, a maximum accepted gap of 0.15 s, and a physical tracking speed bound
of 720°/s. The gap and speed bounds are validated so their product plus a small quantization
margin is less than 180°. A reported displacement exceeding the speed bound, a delayed
sample, invalid feedback, a serial error or travel beyond the configured window faults
the loop. Keep manual leader motion within the tracking bound.

A tracking fault is latched, commands zero speed when communication permits, and rejects
further actions/observations. Stop the fixture, inspect the cause and reconnect in a known
task starting arrangement. Never guess a missing turn count. Do not loosen tracking limits
just to conceal serial or scheduling failures.

A separate action watchdog commands zero speed when no new rotation target arrives for
`command_timeout_s` (default 1 s). Fresh valid commands resume following if tracking is
still healthy. This also applies if policy inference stalls: adjust inference speed or
the timeout deliberately after checking the consequences. No automatic return home occurs.

Disconnect requests worker termination and acknowledged zero speed before closing the
serial bus, then disables torque by default. Stop-packet failures are reported. A worker
that cannot terminate retains the bus instead of closing a serial handle under a live
transaction. A serial fault can prevent every software stop request from reaching the
servo. A computer/process crash can leave the last velocity command active. **Keep a
physical servo-power cutoff available during testing and operation.** This host watchdog
is not a hardware watchdog.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `rotation_control` | `continuous` | Cumulative position following via velocity mode |
| `rotation_min_deg`, `rotation_max_deg` | -720, +720 | Session travel/target window; choose mechanically valid limits |
| `control_hz` | 50 | Background encoder/control frequency |
| `max_tracking_gap_s` | 0.15 | Largest trustworthy sample gap |
| `max_tracking_speed_deg_s` | 720 | Assumed bound on actual shaft motion, including passive leader |
| `rotation_kp` | 2 | Proportional position gain, per second under the raw speed convention |
| `rotation_tolerance_deg` | 0.5 | Zero-speed position deadband |
| `rotation_speed` | 400 | Maximum magnitude of raw rotation speed command |
| `rotation_velocity_sign` | +1 | Raw speed direction relative to increasing encoder counts |
| `command_timeout_s` | 1 | Stop when no fresh rotation command is received |
| `rotation_homing_offset` | 0 | Fixed encoder offset, saved at calibration; not physical session home |
| `max_relative_target` | null | Optional per-action cap from current pose |

Relative caps use degrees for rotation and percentage points for gripper. A dictionary
must contain both `rotation` and `gripper`, without `.pos`. The native recorder stores the
requested action before robot-side clipping. The documented CLI commands leave this cap disabled and limit
speed in the controller instead. Speed limits do not make a cable-safe mechanical window
optional; multiple revolutions can still wind up wiring or an attached object.

## Optional single-turn fallback

If bench tests show velocity mode is unsuitable on your hardware, explicitly configure
**both** leader and follower with `rotation_control="single_turn"`,
`rotation_min_deg=0`, and `rotation_max_deg=359.912109375` (or a narrower safe window).
This uses native position commands and absolute bounded encoder coordinates. With the
default `stop_on_encoder_wrap=true`, observed or requested jumps over 180° latch a fault.
It permits greater-than-180° total motion inside the window, but cannot execute the
200° + 190° sequence as cumulative 390°. Disabling the guard does not add multi-turn
control. That fallback requires your mechanical workaround and its own fresh dataset.

Source references: `src/lerobot/motors/feetech/feetech.py`,
`motors/feetech/tables.py`, and `robots/lekiwi/lekiwi.py`, under the bundled checkout.

## CLI settings

For a standalone follower, pass parameters as `--robot.rotation_speed=300`,
`--robot.rotation_min_deg=-450`, and so on. For the combined follower use
`--robot.left_arm_config.rotation_speed=300`. Leader equivalents begin with `--teleop`.
Ports are required on the CLI: `--robot.port=COM16` for standalone or
`--robot.left_arm_config.port=COM16 --robot.right_arm_config.port=COM15` for combined.
The right side is the SO-100. No COM port is fixed in device code.
