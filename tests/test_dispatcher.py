"""Tests for Dispatcher."""

from __future__ import annotations

from unittest.mock import patch

from actions.dispatcher import Dispatcher

_PROFILE = {
    "name": "Test",
    "app": "",
    "shortcuts": {
        "next":     "RIGHT",
        "prev":     "LEFT",
        "zoom_in":  "CMD+EQUAL",
        "zoom_out": "CMD+MINUS",
    },
}


def _make_dispatcher(**kwargs) -> Dispatcher:
    return Dispatcher(_PROFILE, gate_window=False, **kwargs)


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

def test_initial_state_is_active():
    d = _make_dispatcher()
    assert d.state == "active"


def test_fist_toggles_to_paused():
    d = _make_dispatcher()
    result = d.dispatch("fist")
    assert d.state == "paused"
    assert result == "pause_toggle"


def test_fist_toggles_back_to_active():
    d = _make_dispatcher()
    d.dispatch("fist")
    d.dispatch("fist")
    assert d.state == "active"


def test_gestures_suppressed_when_paused():
    d = _make_dispatcher()
    d.dispatch("fist")  # → paused
    result = d.dispatch("next_slide")
    assert result is None


# ---------------------------------------------------------------------------
# Shortcut dispatch
# ---------------------------------------------------------------------------

@patch("actions.dispatcher._send_pynput", return_value=True)
def test_next_slide_sends_right(mock_send):
    d = _make_dispatcher()
    action = d.dispatch("next_slide")
    assert action == "next"
    mock_send.assert_called_once_with("RIGHT")


@patch("actions.dispatcher._send_pynput", return_value=True)
def test_prev_slide_sends_left(mock_send):
    d = _make_dispatcher()
    action = d.dispatch("prev_slide")
    assert action == "prev"
    mock_send.assert_called_once_with("LEFT")


@patch("actions.dispatcher._send_pynput", return_value=True)
def test_zoom_in_sends_shortcut(mock_send):
    d = _make_dispatcher()
    action = d.dispatch("zoom_in")
    assert action == "zoom_in"
    mock_send.assert_called_once_with("CMD+EQUAL")


@patch("actions.dispatcher._send_pynput", return_value=True)
def test_zoom_out_sends_shortcut(mock_send):
    d = _make_dispatcher()
    action = d.dispatch("zoom_out")
    assert action == "zoom_out"
    mock_send.assert_called_once_with("CMD+MINUS")


def test_unknown_gesture_returns_none():
    d = _make_dispatcher()
    assert d.dispatch("wave") is None


# ---------------------------------------------------------------------------
# Active-app gating
# ---------------------------------------------------------------------------

def test_gate_blocks_when_app_not_running():
    profile = {**_PROFILE, "app": "Microsoft PowerPoint"}
    d = Dispatcher(profile, gate_window=True)
    with patch("actions.dispatcher._app_is_running", return_value=False):
        result = d.dispatch("next_slide")
    assert result is None


@patch("actions.dispatcher._send_pynput", return_value=True)
def test_gate_allows_when_app_running(mock_send):
    profile = {**_PROFILE, "app": "Microsoft PowerPoint"}
    d = Dispatcher(profile, gate_window=True)
    with patch("actions.dispatcher._app_is_running", return_value=True):
        result = d.dispatch("next_slide")
    assert result == "next"
