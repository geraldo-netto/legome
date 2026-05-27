"""Unit tests for legome.display (headless paths only)."""

import sys
import types
from typing import Any

import numpy as np

from legome import display


def test_has_display_no_env(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr(display.os, "name", "posix")
    assert display.has_display() is False


def test_has_display_x11(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(display.os, "name", "posix")
    assert display.has_display() is True


def test_has_display_wayland(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setattr(display.os, "name", "posix")
    assert display.has_display() is True


def test_has_display_windows(monkeypatch):
    monkeypatch.setattr(display.os, "name", "nt")
    assert display.has_display() is True


def test_show_image_skips_when_no_display(monkeypatch):
    monkeypatch.setattr(display, "has_display", lambda: False)
    img = np.zeros((2, 2, 3), dtype=np.uint8)
    assert display.show_image(img) is False


def test_show_image_skips_when_cv2_missing(monkeypatch):
    monkeypatch.setattr(display, "has_display", lambda: True)
    # Force ImportError for cv2 by removing from sys.modules and blocking re-import.
    monkeypatch.setitem(sys.modules, "cv2", None)
    img = np.zeros((2, 2, 3), dtype=np.uint8)
    assert display.show_image(img) is False


def test_show_image_invokes_cv2_loop(monkeypatch):
    """When display + cv2 are present, show_image drives the cv2 GUI loop."""
    calls: dict[str, Any] = {
        "namedWindow": 0,
        "imshow": 0,
        "destroyAllWindows": 0,
        "wait": 0,
    }
    visible_states = [1, 1, 0]  # visible for two iterations, then closed

    class WND:
        WINDOW_KEEPRATIO = 1
        WINDOW_NORMAL = 2
        WND_PROP_VISIBLE = 1
        INTER_NEAREST = 0
        error = RuntimeError

        @staticmethod
        def resize(image, size, interpolation=None):
            import numpy as np

            w, h = size
            return np.zeros((h, w, 3), dtype=np.uint8)

        @staticmethod
        def namedWindow(title, flag):
            calls["namedWindow"] += 1
            calls["last_flag"] = flag

        @staticmethod
        def resizeWindow(title, w, h):
            calls["resizeWindow"] = (w, h)

        @staticmethod
        def imshow(title, img):
            calls["imshow"] += 1

        @staticmethod
        def getWindowProperty(title, prop):
            return visible_states.pop(0)

        @staticmethod
        def waitKey(ms):
            calls["wait"] += 1
            return 0  # not 'q'

        @staticmethod
        def destroyAllWindows():
            calls["destroyAllWindows"] += 1

    fake_cv2 = types.ModuleType("cv2")
    for k in dir(WND):
        if not k.startswith("_"):
            setattr(fake_cv2, k, getattr(WND, k))
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.setattr(display, "has_display", lambda: True)

    img = np.zeros((2, 2, 3), dtype=np.uint8)
    assert display.show_image(img, wait_ms=1) is True
    assert calls["namedWindow"] == 1
    assert calls["imshow"] == 1
    assert calls["destroyAllWindows"] == 1
    assert calls["wait"] >= 1
    # Window must be opened in NORMAL | KEEPRATIO mode so the image
    # follows the borders of the preview window.
    assert calls["last_flag"] == (WND.WINDOW_NORMAL | WND.WINDOW_KEEPRATIO)
    # 2x2 input is pre-upscaled by show_image to MIN_PREVIEW_AXIS_PX=800 along
    # the longest axis, so the window opens at the upscaled size.
    assert calls["resizeWindow"] == (display.MIN_PREVIEW_AXIS_PX, display.MIN_PREVIEW_AXIS_PX)


def test_show_image_downscales_oversized_canvas(monkeypatch):
    """A canvas larger than TARGET_PREVIEW_{W,H} must take the cv2.INTER_AREA path."""
    calls = {"resize_interp": None}
    visible_states = [1, 0]

    class WND:
        WINDOW_KEEPRATIO = 1
        WINDOW_NORMAL = 2
        WND_PROP_VISIBLE = 1
        INTER_NEAREST = 0
        INTER_AREA = 3
        error = RuntimeError

        @staticmethod
        def resize(image, size, interpolation=None):
            calls["resize_interp"] = interpolation
            w, h = size
            return np.zeros((h, w, 3), dtype=np.uint8)

        @staticmethod
        def namedWindow(*a, **k):
            pass

        @staticmethod
        def resizeWindow(*a, **k):
            pass

        @staticmethod
        def imshow(*a, **k):
            pass

        @staticmethod
        def getWindowProperty(*a, **k):
            return visible_states.pop(0)

        @staticmethod
        def waitKey(ms):
            return 0

        @staticmethod
        def destroyAllWindows():
            pass

    fake_cv2 = types.ModuleType("cv2")
    for k in dir(WND):
        if not k.startswith("_"):
            setattr(fake_cv2, k, getattr(WND, k))
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.setattr(display, "has_display", lambda: True)

    # 4000 x 3000 canvas — larger than the 1400 x 1000 preview budget, so
    # show_image must downscale via INTER_AREA (build-plan path).
    huge = np.zeros((3000, 4000, 3), dtype=np.uint8)
    assert display.show_image(huge, wait_ms=1) is True
    assert calls["resize_interp"] == WND.INTER_AREA


def test_show_image_quits_on_q(monkeypatch):
    visible_states = [1, 1]

    class WND:
        WINDOW_KEEPRATIO = 1
        WINDOW_NORMAL = 2
        WND_PROP_VISIBLE = 1
        INTER_NEAREST = 0
        error = RuntimeError

        @staticmethod
        def resize(image, size, interpolation=None):
            import numpy as np

            w, h = size
            return np.zeros((h, w, 3), dtype=np.uint8)

        @staticmethod
        def namedWindow(*a, **k):
            pass

        @staticmethod
        def resizeWindow(*a, **k):
            pass

        @staticmethod
        def imshow(*a, **k):
            pass

        @staticmethod
        def getWindowProperty(*a, **k):
            return visible_states.pop(0)

        @staticmethod
        def waitKey(ms):
            return ord("q")

        @staticmethod
        def destroyAllWindows():
            pass

    fake_cv2 = types.ModuleType("cv2")
    for k in dir(WND):
        if not k.startswith("_"):
            setattr(fake_cv2, k, getattr(WND, k))
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.setattr(display, "has_display", lambda: True)

    img = np.zeros((2, 2, 3), dtype=np.uint8)
    assert display.show_image(img, wait_ms=1) is True
