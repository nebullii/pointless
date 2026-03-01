"""Tests for Dispatcher state machine and shortcut parsing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from actions.dispatcher import Dispatcher, _parse_shortcut

# ---------------------------------------------------------------------------
# _parse_shortcut
# ---------------------------------------------------------------------------

def test_parse_arrow():
    from pynput import keyboard as kb
    mods, key = _parse_shortcut("RIGHT")
    assert mods == [] and key == kb.Key.right


def test_parse_modifier_combo():
    from pynput import keyboard as kb
    mods, key = _parse_shortcut("CMD+SHIFT+L")
    assert kb.Key.cmd in mods and kb.Key.shift in mods
    assert key == "l"


def test_parse_unknown_returns_none_key():
    mods, key = _parse_shortcut("UNKNOWN_KEY")
    assert key is None


# ---------------------------------------------------------------------------
# Dispatcher state machine
# ---------------------------------------------------------------------------

_PROFILE = {
    "name": "Test",
    "app": "",
    "shortcuts": {
        "next":    "RIGHT",
        "prev":    "LEFT",
        "pointer": "SHIFT+L",
        "blank":   "B",
    },
}


def _make_dispatcher(**kwargs) -> Dispatcher:
    return Dispatcher(_PROFILE, gate_window=False, **kwargs)


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
    result = d.dispatch("swipe_right")
    assert result is None


@patch("actions.dispatcher._send_shortcut")
def test_swipe_right_sends_next(mock_send):
    d = _make_dispatcher()
    action = d.dispatch("swipe_right")
    assert action == "next"
    mock_send.assert_called_once_with("RIGHT")


@patch("actions.dispatcher._send_shortcut")
def test_swipe_left_sends_prev(mock_send):
    d = _make_dispatcher()
    action = d.dispatch("swipe_left")
    assert action == "prev"
    mock_send.assert_called_once_with("LEFT")


@patch("actions.dispatcher._send_shortcut")
def test_open_palm_sends_pointer(mock_send):
    d = _make_dispatcher()
    action = d.dispatch("open_palm")
    assert action == "pointer"
    mock_send.assert_called_once_with("SHIFT+L")


@patch("actions.dispatcher._send_shortcut")
def test_pinch_sends_blank(mock_send):
    d = _make_dispatcher()
    action = d.dispatch("pinch")
    assert action == "blank"
    mock_send.assert_called_once_with("B")


def test_unknown_gesture_returns_none():
    d = _make_dispatcher()
    assert d.dispatch("wave") is None


# ---------------------------------------------------------------------------
# Active-window gating
# ---------------------------------------------------------------------------

def test_window_gate_blocks_when_wrong_app():
    profile = {**_PROFILE, "app": "Microsoft PowerPoint"}
    d = Dispatcher(profile, gate_window=True)
    with patch("actions.dispatcher._frontmost_app", return_value="Google Chrome"):
        result = d.dispatch("swipe_right")
    assert result is None


@patch("actions.dispatcher._send_shortcut")
def test_window_gate_allows_when_correct_app(mock_send):
    profile = {**_PROFILE, "app": "Microsoft PowerPoint"}
    d = Dispatcher(profile, gate_window=True)
    with patch("actions.dispatcher._frontmost_app", return_value="Microsoft PowerPoint"):
        result = d.dispatch("swipe_right")
    assert result == "next"
