"""Configuration and defaults."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Settings:
    profile: str = "powerpoint_windows"
    camera_index: int = 0
    show_overlay: bool = True
    presentation_file: Optional[str] = field(default=None)
