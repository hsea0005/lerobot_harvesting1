"""Motor and camera fakes used by hardware-free regression tests."""

from contextlib import contextmanager


class FakeBus:
    instances = []

    def __init__(self, port, motors, calibration=None):
        self.port, self.motors = port, motors
        self.calibration = calibration or {}
        self.is_connected = False
        self.torque_enabled = False
        self.positions = {name: 2048 for name in motors}
        self.operations = []
        self.fail_connect = False
        self.fail_disconnect = False
        FakeBus.instances.append(self)

    @property
    def is_calibrated(self):
        return bool(self.calibration)

    def connect(self):
        self.is_connected = True
        if self.fail_connect:
            raise OSError("Fake connect failure")

    def disconnect(self, disable_torque=True):
        self.operations.append(("disconnect", disable_torque))
        if self.fail_disconnect and disable_torque:
            raise OSError("Fake torque disable failure")
        self.is_connected = False

    def disable_torque(self):
        self.torque_enabled = False
        self.operations.append(("torque", False))

    def enable_torque(self):
        self.torque_enabled = True
        self.operations.append(("torque", True))

    @contextmanager
    def torque_disabled(self):
        self.disable_torque()
        yield
        self.enable_torque()

    def configure_motors(self, **kwargs):
        self.operations.append(("configure", kwargs))

    def write(self, register, motor, value, **kwargs):
        self.operations.append(("write", register, motor, value))

    def read(self, register, motor, normalize=True, **kwargs):
        if register != "Torque_Enable":
            raise ValueError(f"Unsupported fake register: {register}")
        self.operations.append(("read", register, motor))
        return int(self.torque_enabled)

    def sync_read(self, register, motors=None, normalize=True, **kwargs):
        names = [motors] if isinstance(motors, str) else motors or self.motors
        if normalize:
            return {name: 50.0 if name == "gripper" else 0.0 for name in names}
        return {name: self.positions[name] for name in names}

    def sync_write(self, register, values, normalize=True, **kwargs):
        self.operations.append(("goal", register, dict(values), normalize))

    def write_calibration(self, calibration):
        self.calibration = calibration

    def reset_calibration(self, motors=None):
        self.operations.append(("reset", motors))

    def set_half_turn_homings(self, motors=None):
        return {"gripper": 0}

    def record_ranges_of_motion(self, motors=None):
        return {"gripper": 1000}, {"gripper": 3000}

    def setup_motor(self, name):
        self.operations.append(("setup", name))


class FakeCamera:
    width, height, use_rgb = 640, 480, True

    def __init__(self, fail=False):
        self.is_connected = False
        self.fail = fail

    def connect(self):
        self.is_connected = True
        if self.fail:
            raise OSError("Fake camera failure")

    def disconnect(self):
        self.is_connected = False

    def read_latest(self):
        import numpy as np
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)
