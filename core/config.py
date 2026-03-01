"""Configuration and defaults."""

from dataclasses import dataclass


@dataclass
class Settings:
    profile: str = "powerpoint_mac"
    camera_index: int = 0
    show_overlay: bool = True
