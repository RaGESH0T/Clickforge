from clickforge.backends.capabilities import detect_capabilities
from clickforge.backends.hotkeys import (
    UnavailableHotkeyListener,
    WindowsEmergencyStopListener,
    X11EmergencyStopListener,
    create_emergency_stop_listener,
)


def test_windows_backend_is_available():
    result = detect_capabilities({}, platform_name="win32")
    assert result.available
    assert result.session_type == "windows"
    assert result.supports_global_hotkeys
    assert result.supports_position_capture


def test_x11_backend_is_available():
    result = detect_capabilities({"DISPLAY": ":0"}, platform_name="linux")
    assert result.available
    assert result.backend_id == "linux-x11-xtest"
    assert result.session_type == "x11"


def test_wayland_is_rejected_with_a_clear_reason():
    result = detect_capabilities({"WAYLAND_DISPLAY": "wayland-0"}, platform_name="linux")
    assert not result.available
    assert result.session_type == "wayland"
    assert "X11" in result.reason
    assert result.notes


def test_wayland_session_type_alone_is_enough_to_reject():
    result = detect_capabilities(
        {"XDG_SESSION_TYPE": "wayland", "DISPLAY": ":0"},
        platform_name="linux",
    )
    assert not result.available
    assert result.session_type == "wayland"


def test_linux_without_display_is_unavailable():
    result = detect_capabilities({}, platform_name="linux")
    assert not result.available
    assert result.session_type == "none"
    assert "DISPLAY" in result.reason


def test_unknown_platform_is_unavailable():
    result = detect_capabilities({}, platform_name="freebsd")
    assert not result.available
    assert result.session_type == "unknown"
    assert "Windows" in result.reason


def test_emergency_stop_listener_matches_the_session_type():
    x11 = detect_capabilities({"DISPLAY": ":0"}, platform_name="linux")
    assert isinstance(create_emergency_stop_listener(x11, lambda: None), X11EmergencyStopListener)

    windows = detect_capabilities({}, platform_name="win32")
    assert isinstance(
        create_emergency_stop_listener(windows, lambda: None),
        WindowsEmergencyStopListener,
    )

    wayland = detect_capabilities({"WAYLAND_DISPLAY": "wayland-0"}, platform_name="linux")
    unavailable = create_emergency_stop_listener(wayland, lambda: None)
    assert isinstance(unavailable, UnavailableHotkeyListener)
    assert unavailable.start() is False
