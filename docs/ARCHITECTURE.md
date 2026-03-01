# Pointless Architecture

## Pipeline
1. Capture frames from webcam
2. Run hand tracking to get landmarks
3. Extract features + classify gestures
4. Map gestures to commands in current context
5. Emit OS-level key events
6. Show minimal overlay feedback

## Core Modules
- `vision.capture`: camera acquisition
- `vision.tracker`: hand landmarks
- `gestures.engine`: pipeline + smoothing
- `gestures.rules`: rule-based classifier
- `actions.dispatcher`: state machine + debouncing
- `actions.profiles`: app-specific shortcuts
- `ui.overlay`: HUD + calibration
