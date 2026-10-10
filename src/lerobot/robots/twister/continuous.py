"""Continuously sample encoder positions and follow cumulative angle targets.

The servo uses its native velocity mode; the LeRobot action remains a position.
All access to the shared two-servo serial bus uses the same lock.
"""

import threading
import time
from collections.abc import Callable

from .control import PositionVelocityController, RotationTrackingError, UnwrappedEncoder


class ContinuousRotationLoop:
    def __init__(self, bus, bus_lock, config, *, actuate: bool,
                 clock: Callable[[], float] = time.perf_counter):
        self.bus, self.bus_lock, self.config = bus, bus_lock, config
        # perf_counter is monotonic and high-resolution on Windows Python 3.12.
        self.clock = clock
        self.tracker = UnwrappedEncoder(config.max_tracking_gap_s, config.max_tracking_speed_deg_s)
        self.controller = PositionVelocityController(
            config.rotation_kp, config.rotation_speed, config.rotation_tolerance_deg,
            config.command_timeout_s, config.rotation_velocity_sign,
        )
        self.enabled = actuate
        self._state_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._error: Exception | None = None
        self._raw: dict[str, int | float] = {}
        self._angle = 0.0
        self._sample_time: float | None = None
        self._stop_error: Exception | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        self.sample_once()  # Establish zero without any home-position movement.
        self._thread = threading.Thread(target=self._run, name="twister-rotation", daemon=True)
        self._thread.start()

    def sample_once(self) -> None:
        with self.bus_lock:
            raw = self.bus.sync_read("Present_Position", normalize=False,
                                     num_retry=self.config.num_read_retries)
            now = self.clock()
            with self._state_lock:
                if self._error:
                    raise self._error
                angle = self.tracker.update(raw["rotation"], now)
                margin = self.config.rotation_tolerance_deg
                if not self.config.rotation_min_deg - margin <= angle <= self.config.rotation_max_deg + margin:
                    raise RotationTrackingError("Actual cumulative rotation exceeded the configured travel limits.")
                self._raw, self._angle, self._sample_time = dict(raw), angle, now
                velocity = self.controller.velocity(angle, now, enabled=self.enabled)
                enabled = self.enabled
            if enabled:
                # write (acknowledged), not sync_write, so packet errors terminate control.
                self.bus.write("Goal_Velocity", "rotation", velocity, normalize=False)

    def _run(self) -> None:
        period = 1.0 / self.config.control_hz
        try:
            deadline = self.clock()
            while not self._stop_event.is_set():
                deadline += period
                if self._stop_event.wait(max(0.0, deadline - self.clock())):
                    break
                self.sample_once()
                if self.clock() - deadline > period:
                    deadline = self.clock()
        except Exception as exc:
            self.fail(exc)
        finally:
            self._write_stop()

    def fail(self, error: Exception) -> None:
        with self._state_lock:
            if self._error is None:
                self._error = error
        self._stop_event.set()

    def snapshot(self) -> tuple[float, dict[str, int | float]]:
        with self._state_lock:
            if self._error:
                raise RotationTrackingError(f"Rotation control fault: {self._error}") from self._error
            if self._sample_time is None or self.clock() - self._sample_time > self.config.max_tracking_gap_s:
                error = RotationTrackingError("Rotation feedback is stale; reconnect to restore a trusted turn count.")
                self._error = error
                self._stop_event.set()
                raise error
            return self._angle, dict(self._raw)

    def set_target(self, target_deg: float) -> None:
        # Fail before accepting another action if background tracking has stopped.
        self.snapshot()
        with self._state_lock:
            if not self.config.rotation_min_deg <= target_deg <= self.config.rotation_max_deg:
                raise ValueError("Cumulative rotation target is outside the configured travel window.")
            self.controller.set_target(target_deg, self.clock())

    def set_enabled(self, enabled: bool) -> None:
        with self._state_lock:
            self.enabled = enabled
            self.controller.last_command = None
        if not enabled:
            self._write_stop()

    def _write_stop(self) -> None:
        if not self.bus_lock.acquire(timeout=0.5):
            self._stop_error = RotationTrackingError("Serial bus lock unavailable while stopping rotation.")
            self.fail(self._stop_error)
            return
        try:
            if self.bus.is_connected:
                self.bus.write("Goal_Velocity", "rotation", 0, normalize=False, num_retry=1)
        except Exception as exc:
            self._stop_error = exc
            self.fail(exc)
        finally:
            self.bus_lock.release()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=5.0)
            if self.is_running:
                raise RuntimeError("Rotation worker did not stop; the serial connection is not responding.")
        self._write_stop()
        if self._stop_error:
            raise RuntimeError(f"Rotation stop failed: {self._stop_error}") from self._stop_error
