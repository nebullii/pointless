"""Quick sanity-check for gesture direction and key dispatch."""
import sys
sys.path.insert(0, ".")

from collections import deque
from gestures.rules import classify, WAVE_THRESHOLD, PINCH_THRESHOLD

# ── Wave LEFT (x increasing → user's left hand sweeps leftward) ─────────────
h = deque(maxlen=30)
triggered = []
for i in range(16):
    x = 0.30 + (i / 15) * 0.25       # 0.30 → 0.55  (delta +0.25, well above 0.18)
    lms = [(x, 0.5, 0)] + [(0.1, 0.1, 0)] * 20
    g, c = classify(lms, h)
    if g:
        triggered.append((g, round(c, 2)))

assert any(g == "next_slide" for g, _ in triggered), f"wave-left should fire next_slide, got {triggered}"
print(f"[PASS] wave-left  -> {triggered}")

# ── Wave RIGHT (x decreasing) ────────────────────────────────────────────────
h2 = deque(maxlen=30)
triggered2 = []
for i in range(16):
    x = 0.70 - (i / 15) * 0.25       # 0.70 → 0.45  (delta -0.25)
    lms = [(x, 0.5, 0)] + [(0.1, 0.1, 0)] * 20
    g, c = classify(lms, h2)
    if g:
        triggered2.append((g, round(c, 2)))

assert any(g == "prev_slide" for g, _ in triggered2), f"wave-right should fire prev_slide, got {triggered2}"
print(f"[PASS] wave-right -> {triggered2}")

# ── Pinch OPEN (thumb-index distance increasing) ─────────────────────────────
# Need >= 15 frames before classify() starts returning detections.
# Warm up with 15 neutral frames, then let distance grow clearly above threshold.
import math
h3 = deque(maxlen=30)
triggered3 = []
THUMB_POS = (0.0, 0.0, 0.0)
# 15 neutral frames: thumb at origin, index 0.04 away
for _ in range(15):
    lms = [(0.5, 0.5, 0), (0,0,0), (0,0,0), (0,0,0), THUMB_POS,
           (0,0,0), (0,0,0), (0,0,0), (0.04, 0, 0),
           (0.1,0.1,0),(0.1,0.1,0),(0.1,0.1,0),(0.1,0.1,0),
           (0.1,0.1,0),(0.1,0.1,0),(0.1,0.1,0),(0.1,0.1,0),
           (0.1,0.1,0),(0.1,0.1,0),(0.1,0.1,0),(0.1,0.1,0)]
    classify(lms, h3)
# 13 more frames: index spreads from 0.04 → 0.20 (delta +0.16 over 13 frames)
for i in range(13):
    d = 0.04 + (i / 12) * 0.16       # 0.04 → 0.20
    lms = [(0.5, 0.5, 0), (0,0,0), (0,0,0), (0,0,0), THUMB_POS,
           (0,0,0), (0,0,0), (0,0,0), (d, 0, 0),
           (0.1,0.1,0),(0.1,0.1,0),(0.1,0.1,0),(0.1,0.1,0),
           (0.1,0.1,0),(0.1,0.1,0),(0.1,0.1,0),(0.1,0.1,0),
           (0.1,0.1,0),(0.1,0.1,0),(0.1,0.1,0),(0.1,0.1,0)]
    g, c = classify(lms, h3)
    if g:
        triggered3.append((g, round(c, 2)))

assert any(g == "zoom_in" for g, _ in triggered3), f"pinch-open should fire zoom_in, got {triggered3}"
print(f"[PASS] pinch-open  -> {triggered3}")

# ── Key alias check ──────────────────────────────────────────────────────────
from actions.dispatcher import _KEY_ALIASES
assert _KEY_ALIASES["EQUAL"] == "equal", f"EQUAL alias wrong: {_KEY_ALIASES['EQUAL']}"
assert _KEY_ALIASES["MINUS"] == "minus", f"MINUS alias wrong: {_KEY_ALIASES['MINUS']}"
print("[PASS] key aliases correct (EQUAL=equal, MINUS=minus)")

print("\nAll checks passed.")
