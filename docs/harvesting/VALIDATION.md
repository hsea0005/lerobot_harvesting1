> Historical report from the supplied ZIP, retained for provenance. Paths and test results
> below describe that standalone bundle. See [INTEGRATION.md](INTEGRATION.md) for this native copy.

# Validation report — 2026-10-05

Target source: the user's uploaded `lerobot-main(1).zip`, version 0.6.2, Python >=3.12.
The copy in `lerobot-main/` has no source modifications. Custom plugin version: 1.2.0.

## Completed

- Compiled/parsed custom Python files and tokenized all 23 documented CLI commands.
- Compared all 1,150 original uploaded files byte-for-byte: zero changes.
- Built an installable wheel; distribution Name is exactly `lerobot_robot_harvesting`,
  matching the uploaded plugin discoverer's required prefix.
- Executed **71 tests**, all passing, in `python tests/run_offline.py`.
- Checked direct-drive 200° alignment followed by another 190° (390° cumulative), arbitrary
  initial encoder angles, forward/reverse seam crossings, repeated turns and return to zero.
- Checked delayed/impossible/ambiguous feedback rejection and latched tracking faults.
- Checked position-to-velocity output, speed cap, tolerance, direction, overshoot correction,
  and stale-action watchdog stop/resume. An ideal mathematical plant reaches 200° then 390°;
  this is a logic check, not a simulation of real servo dynamics or object contact.
- Checked rotation velocity mode, gripper position mode, zero startup speed, passive leader,
  and absence of rotation Goal_Position writes in continuous mode.
- Checked worker termination before serial disconnect, read-fault stops, stop-packet failure
  reporting, shared serial locking, partial camera connection cleanup and hung-worker handling.
- Checked calibration-CLI startup (`connect(calibrate=False)`), saved calibration reuse and
  worker shutdown before interactive calibration.
- Checked real bundled Robot/Teleoperator factory construction, feature availability before
  connection, eight-joint ordering/routing and a combined 390° Twister + six-joint SO100 action.
- Checked gripper conversion/inversion, relative command clipping, malformed/non-finite
  command rejection, and fallback single-turn encoder conversions and boundary guards.
- Checked every documented CLI option name against bundled dataclass/AST declarations, including
  `env_eval_freq`, dataset `no_stamp`, and the `lerobot-rollout` policy path convention.
- Executed the upstream feature-conversion function extracted from its source AST; checked
  eight-element action/state vectors, feature names and RGB camera feature shape.
- Checked direct-drive simulation radians/degrees round trips preserving 390° and joint order.
- Checked native bimanual `left_arm_config` / `right_arm_config` conventions, the requested
  port roles in all examples, and forwarding arbitrary ports, motor IDs and tuning parameters.
- Confirmed custom presets were removed and all six workflows are documented as CLI commands.

## Test boundaries

The execution environment did not contain LeRobot's runtime dependencies. Installing the
required draccus package from the available index and explicit PyPI failed with no available
distributions; real CLI parsing remains unexecuted here. The offline runner substitutes
external draccus/Torch/Hub/progress imports only; it loads real bundled LeRobot Robot, Teleoperator,
motor definitions, decorators, SO classes and device factories. Motor buses and cameras
are mocked. It does not substitute custom robot logic.

These tests do **not** establish real draccus CLI decoding, SDK packet behavior, installed
full-stack imports, serial reliability, servo firmware behavior, motor direction/speed
under load, physical overshoot, torque protection, completed dataset recording, training,
inference, or LeIsaac task execution. AST checks establish field-name compatibility rather
than full runtime CLI parsing. The wheel build checks packaging rather than complete
installation of all dependencies.

`verify_install.py` checks real installed-plugin discovery, dependency imports, factory
construction, matching continuous leader/follower settings and real CLI parsing of the
documented commands, without connecting motors. The script parses setup, calibration,
teleoperation and recording with native upstream config classes, plus rollout hardware
arguments without loading a checkpoint. Run it on your PC after installation. Run the
normal unittest suite there with real dependencies and mocked hardware. Complete the unloaded forward,
reverse, seam-crossing, 200°→390°, return and stop checks in the README before using the
mechanism on an object. Tune controller settings against measured response.

Cumulative turn count is a host-side estimate requiring timely bounded motion; it is not
retained after reconnect or power loss. The action watchdog cannot stop an unreachable
servo or survive a host crash. LeIsaac geometry/environment integration remains deferred;
only the stable joint contract and direct-drive conversion helpers are included.
