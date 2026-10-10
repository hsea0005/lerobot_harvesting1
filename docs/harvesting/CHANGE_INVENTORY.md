> Historical report from the supplied ZIP, retained for provenance. Paths and test results
> below describe that standalone bundle. See [INTEGRATION.md](INTEGRATION.md) for this native copy.

# Change inventory

The original uploaded `lerobot-main/` source is included as-is. No files in that checkout
were edited. There is no need to overwrite an existing LeRobot source directory to use
the plugin with a compatible installed version.

New custom files:

| File | Purpose |
|---|---|
| `plugins/harvesting/pyproject.toml` | Installable plugin distribution and version constraint |
| `src/lerobot_robot_harvesting/__init__.py` | Exposes registered configs and matching implementation classes |
| `config.py` | `twister`, `twister_leader`, `bimanual_harvesting`, `bimanual_harvesting_leader` registrations |
| `control.py` | Unwrapped encoder, cumulative position controller, conversions and fallback guard |
| `continuous.py` | Background feedback/control worker, shared serial lock, watchdog and stop handling |
| `device.py` | Common Feetech motor setup, calibration, configuration and resource lifecycle |
| `twister.py` | Two-joint follower plus optional cameras |
| `twister_leader.py` | Matching passive two-joint leader |
| `pair.py` | Combined-device connection, calibration, cleanup and routing helpers |
| `bimanual_harvesting.py` | Twister + standard SO100 follower under one Robot |
| `bimanual_harvesting_leader.py` | Twister + standard SO100 leader under one Teleoperator |
| `simulation.py` | Future simulation order/unit conversion helpers |

Implementation files above are under `plugins/harvesting/src/lerobot_robot_harvesting/`.
The bundle also adds `verify_install.py`, six test-support/test files,
the README and these documentation files.

No robot factory switch, dataset serializer, policy architecture, training loop,
recording loop, rollout implementation or hardware SDK was forked. The installation
uses the documented plugin prefix, registry decorators, class/config naming convention
and exports so the native CLI can discover the additions.

Version 1.1 replaces the initial bounded rotation default with continuous direct-drive
following. The fixture uses cumulative coordinates and configurable session travel limits.
The simulation helpers map those degrees to radians directly.
No changes to upstream policy or dataset formats were needed, but rotation semantics
differ from version 1.0, so its datasets/checkpoints must not be mixed with version 1.1.

Version 1.2 removes the custom JSON preset directory. The combined hardware configuration
uses `left_arm_config` (Twister) and `right_arm_config` (SO-100), matching the uploaded
native bimanual CLI naming. README commands supply all ports and runtime settings through
CLI flags, using COM13 SO-100 leader, COM14 Twister leader, COM15 SO-100 follower and
COM16 Twister follower. No port is fixed in runtime code. The verifier parses those command
arguments with real dependencies after installation. Joint features and calibration ID
suffixes are preserved, so this interface change does not invalidate compatible v1.1 data.
