"""Pair lifecycle and routing helpers; do not depend on a symmetric embodiment."""

from typing import Any

from lerobot.utils.decorators import check_if_already_connected

from lerobot.robots.twister.device import TwisterDeviceMixin


def prefixed(values: dict, prefix: str) -> dict:
    return {f"{prefix}_{key}": value for key, value in values.items()}


def split(values: dict, prefix: str) -> dict:
    marker = f"{prefix}_"
    return {key.removeprefix(marker): value for key, value in values.items() if key.startswith(marker)}


def close_device(device: Any) -> list[Exception]:
    """Standard SO disconnect decorators cannot handle partially opened cameras."""
    errors = []
    if isinstance(device, TwisterDeviceMixin):
        # Twister owns a polling worker and handles partial connections itself.
        try:
            device.disconnect()
        except Exception as exc:
            errors.append(exc)
        return errors
    if device.is_connected:
        try:
            device.disconnect()
            return errors
        except Exception as exc:
            errors.append(exc)
    for camera in getattr(device, "cameras", {}).values():
        if camera.is_connected:
            try:
                camera.disconnect()
            except Exception as exc:
                errors.append(exc)
    if device.bus.is_connected:
        try:
            device.bus.disconnect()
        except Exception as exc:
            errors.append(exc)
            try:
                device.bus.disconnect(disable_torque=False)
            except Exception as close_exc:
                errors.append(close_exc)
    return errors


class HarvestingPairMixin:
    @property
    def is_connected(self) -> bool:
        return self.twister.is_connected and self.arm.is_connected and all(
            camera.is_connected for camera in getattr(self, "_scene_cameras", {}).values()
        )

    @property
    def is_calibrated(self) -> bool:
        return self.twister.is_calibrated and self.arm.is_calibrated

    @check_if_already_connected
    def connect(self, calibrate: bool = True) -> None:
        try:
            self.twister.connect(calibrate)
            self.arm.connect(calibrate)
            for camera in getattr(self, "_scene_cameras", {}).values():
                camera.connect()
        except BaseException:
            try:
                self.disconnect()
            except Exception:
                pass
            raise

    def calibrate(self) -> None:
        self.twister.calibrate()
        self.arm.calibrate()

    def configure(self) -> None:
        self.twister.configure()
        self.arm.configure()

    def setup_motors(self) -> None:
        self.twister.setup_motors()
        self.arm.setup_motors()

    def disconnect(self) -> None:
        errors = []
        for camera in getattr(self, "_scene_cameras", {}).values():
            if camera.is_connected:
                try:
                    camera.disconnect()
                except Exception as exc:
                    errors.append(exc)
        errors.extend(close_device(self.twister))
        errors.extend(close_device(self.arm))
        if errors:
            raise RuntimeError(f"Pair cleanup failed: {errors}") from errors[0]
