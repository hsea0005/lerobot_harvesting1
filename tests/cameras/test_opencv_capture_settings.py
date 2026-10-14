"""Capture configuration regressions; no physical camera is opened."""

import unittest
from unittest.mock import patch

import cv2

from lerobot.cameras.configs import Cv2Backends
from lerobot.cameras.opencv import OpenCVCamera, OpenCVCameraConfig

MODULE = "lerobot.cameras.opencv.camera_opencv"
MJPG = cv2.VideoWriter_fourcc(*"MJPG")
YUY2 = cv2.VideoWriter_fourcc(*"YUY2")


class Capture:
    def __init__(self):
        self.values = {
            cv2.CAP_PROP_FRAME_WIDTH: 640.0,
            cv2.CAP_PROP_FRAME_HEIGHT: 480.0,
            cv2.CAP_PROP_FPS: 15.0,
            cv2.CAP_PROP_FOURCC: YUY2,
        }
        self.operations = []
        self.require_mjpg = False
        self.reset_format_on_resize = False
        self.reset_format_on_fps = False
        self.reject_redundant_settings = False
        self.reject_fourcc = False
        self.reject_fps = False
        self.opened = True

    def isOpened(self):
        return self.opened

    def get(self, prop):
        return self.values.get(prop, 0)

    def set(self, prop, value):
        self.operations.append((prop, value))
        if prop != cv2.CAP_PROP_FOURCC and self.require_mjpg and self.values[cv2.CAP_PROP_FOURCC] != MJPG:
            raise cv2.error("Simulated DirectShow pVih failure during uncompressed negotiation")
        if self.reject_redundant_settings and self.values[prop] == value:
            raise cv2.error("Simulated DirectShow restart on unchanged property")
        if prop == cv2.CAP_PROP_FOURCC and self.reject_fourcc:
            return False
        if prop == cv2.CAP_PROP_FPS and self.reject_fps:
            return False
        self.values[prop] = value
        if prop in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT) and self.reset_format_on_resize:
            self.values[cv2.CAP_PROP_FOURCC] = YUY2
        if prop == cv2.CAP_PROP_FPS and self.reset_format_on_fps:
            self.values[cv2.CAP_PROP_FOURCC] = YUY2
        return True

    def release(self):
        self.opened = False


class CaptureSettingsTests(unittest.TestCase):
    def setUp(self):
        self.patchers = [
            patch(f"{MODULE}.platform.system", return_value="Windows"),
            patch(f"{MODULE}.cv2.VideoCapture", Capture),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def camera(self, capture, *, fourcc="MJPG", width=640, height=480, fps=30):
        camera = OpenCVCamera(OpenCVCameraConfig(
            index_or_path=0, backend=Cv2Backends.DSHOW,
            width=width, height=height, fps=fps, fourcc=fourcc,
        ))
        camera.videocapture = capture
        return camera

    def test_format_selected_before_fps_negotiation(self):
        capture = Capture()
        capture.require_mjpg = True
        camera = self.camera(capture)
        camera._configure_capture_settings()
        self.assertEqual(capture.values[cv2.CAP_PROP_FOURCC], MJPG)
        self.assertEqual(capture.values[cv2.CAP_PROP_FPS], 30)

    def test_unchanged_properties_do_not_restart_capture(self):
        capture = Capture()
        capture.values[cv2.CAP_PROP_FOURCC] = MJPG
        capture.values[cv2.CAP_PROP_FPS] = 30
        capture.reject_redundant_settings = True
        self.camera(capture)._configure_capture_settings()
        self.assertEqual(capture.operations, [])

    def test_resize_format_reset_is_corrected_before_fps(self):
        capture = Capture()
        capture.reset_format_on_resize = True
        camera = self.camera(capture, width=320, height=240)
        set_property = capture.set

        def check_fps(prop, value):
            if prop == cv2.CAP_PROP_FPS and capture.values[cv2.CAP_PROP_FOURCC] != MJPG:
                raise cv2.error("FPS requested before restoring compressed format")
            return set_property(prop, value)

        with patch.object(capture, "set", side_effect=check_fps):
            camera._configure_capture_settings()
        self.assertEqual(capture.values[cv2.CAP_PROP_FRAME_WIDTH], 320)
        self.assertEqual(capture.values[cv2.CAP_PROP_FRAME_HEIGHT], 240)
        self.assertEqual(capture.values[cv2.CAP_PROP_FOURCC], MJPG)
        self.assertEqual(capture.values[cv2.CAP_PROP_FPS], 30)

    def test_fps_format_reset_is_corrected_after_fps(self):
        capture = Capture()
        capture.reset_format_on_fps = True
        self.camera(capture)._configure_capture_settings()
        self.assertEqual(capture.values[cv2.CAP_PROP_FOURCC], MJPG)

    def test_no_fourcc_keeps_default_format(self):
        capture = Capture()
        self.camera(capture, fourcc=None)._configure_capture_settings()
        self.assertEqual(capture.values[cv2.CAP_PROP_FOURCC], YUY2)
        self.assertFalse(any(prop == cv2.CAP_PROP_FOURCC for prop, _ in capture.operations))

    def test_rejected_fourcc_still_reports_fallback(self):
        capture = Capture()
        capture.reject_fourcc = True
        with self.assertLogs(MODULE, level="WARNING") as logs:
            self.camera(capture)._configure_capture_settings()
        self.assertTrue(any("failed to set fourcc=MJPG" in message for message in logs.output))
        self.assertEqual(capture.values[cv2.CAP_PROP_FOURCC], YUY2)

    def test_rejected_fps_still_fails(self):
        capture = Capture()
        capture.reject_fps = True
        with self.assertRaisesRegex(RuntimeError, "failed to set fps"):
            self.camera(capture)._configure_capture_settings()

    def test_non_windows_configuration_remains_valid(self):
        capture = Capture()
        camera = self.camera(capture)
        with patch(f"{MODULE}.platform.system", return_value="Linux"):
            camera._configure_capture_settings()
        self.assertEqual(capture.values[cv2.CAP_PROP_FOURCC], MJPG)
        self.assertEqual(capture.values[cv2.CAP_PROP_FPS], 30)

    def test_configuration_exception_releases_capture(self):
        capture = Capture()
        camera = self.camera(capture)
        camera.videocapture = None
        with (
            patch.object(Capture, "__new__", return_value=capture),
            patch.object(Capture, "__init__", return_value=None),
            patch.object(camera, "_configure_capture_settings", side_effect=cv2.error("settings failed")),
        ):
            with self.assertRaises(cv2.error):
                camera.connect(warmup=False)
        self.assertFalse(capture.opened)
        self.assertIsNone(camera.videocapture)
        self.assertIsNone(camera.thread)


if __name__ == "__main__":
    unittest.main()
