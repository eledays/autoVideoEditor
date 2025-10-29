from __future__ import annotations

from typing import Tuple, Any

from moviepy import CompositeVideoClip, ColorClip, vfx


def compose_vertical(
    clip: Any,
    bg_color: Tuple[int, int, int] = (28, 31, 32),
    out_size: Tuple[int, int] = (1080, 1920),
    crop_box: Tuple[int, int, int, int] = (0, 0, 1080, 1440),
    scale: float = 1.25,
) -> Any:
    video = clip.resized(scale)
    left_part = video.with_effects([vfx.Crop(x1=crop_box[0], y1=crop_box[1], x2=crop_box[2], y2=crop_box[3])])
    background = ColorClip(out_size, color=bg_color, duration=video.duration)
    final_video = CompositeVideoClip([background, left_part.with_position(("center", "center"))])
    return final_video
