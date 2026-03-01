# Pointless

Hand-gesture control for presentations — no clicker, no extra hardware, just your Mac's built-in webcam.

## How it works

```
Webcam frame
    ↓
MediaPipe  (vision/tracker.py)
    → 21 hand landmark coordinates (x, y, z)
    ↓
Gesture classifier  (gestures/rules.py)
    → checks finger extension ratios, wrist x-movement
    → returns ("next_slide", confidence) or ("fist", 1.0) etc.
    ↓
Gesture engine  (gestures/engine.py)
    → swipe stored as pending
    → fist (rising edge) confirms it
    → returns "next_slide" once
    ↓
Dispatcher  (actions/dispatcher.py)
    → looks up profile action for "next_slide" → "next"
    → runs AppleScript:
       tell application "Microsoft PowerPoint"
         go to next slide slide show view of slide show window 1
    ↓
PowerPoint advances the slide
```

Everything runs locally on your Mac. The dispatcher talks to PowerPoint via **AppleScript** — macOS's built-in inter-process communication — so no keyboard focus or Accessibility permission is needed for slide navigation. The loop runs at ~30 fps; total latency from gesture to slide change is under 200 ms.

## Gestures

| Gesture | Action |
|---|---|
| Swipe right (open hand) + Fist | Next slide |
| Swipe left (open hand) + Fist | Previous slide |
| Fist (no pending swipe) | Pause / resume gesture detection |

Swipe requires at least 4 of 5 fingers extended. The fist is **edge-triggered** — it fires once on the open→close transition, so holding the fist does not repeat the action.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

Start your PowerPoint slideshow (F5) before or after launching the app. The camera window floats on top of the presentation.

### Profiles

Pass `-p <profile>` to select a profile:

```bash
python -m app.main -p keynote_mac
python -m app.main -p googleslides_web
```

Available profiles: `powerpoint_mac`, `keynote_mac`, `googleslides_web`, `zoom`, `google_meet`.

### Options

| Flag | Description |
|---|---|
| `-p / --profile` | Profile name (default: `powerpoint_mac`) |
| `-c / --camera` | Camera index (default: `0`) |
| `--no-gate` | Skip app-running check |

## Structure

| Path | Purpose |
|---|---|
| `app/main.py` | Entry point — camera loop, HUD |
| `vision/tracker.py` | MediaPipe hand landmark tracking |
| `gestures/rules.py` | Finger extension + fist + swipe classification |
| `gestures/engine.py` | Pending-swipe state machine, cooldown, edge-triggered fist |
| `actions/dispatcher.py` | Gesture → AppleScript / pynput keystroke |
| `profiles/` | Per-app shortcut JSON files |
| `tests/` | Pytest suite (22 tests) |

## Running tests

```bash
python -m pytest tests/
```
