from __future__ import annotations

from typing import List, Sequence, Any

from moviepy import concatenate_videoclips, vfx

from src.domain.entities import Segment


def split_to_clips(video: Any, non_silences: Sequence[Segment]) -> List[Any]:
    clips: List[Any] = []
    for seg in non_silences:
        dl = 0.3
        start = max(0.0, seg.start - dl)
        end = min(video.duration, seg.end + dl)
        # MoviePy v2: метод называется subclipped
        clips.append(video.subclipped(start, end))
    return clips


def speed_up_segment(full_video: Any, clip: Any, non_silences: Sequence[Segment], i: int) -> Any:
    start = non_silences[i].end
    end = non_silences[i + 1].start if i + 1 < len(non_silences) else None

    # MoviePy v2: метод называется subclipped
    video_piece = full_video.subclipped(start, end).without_audio()
    audio_piece = clip.audio

    if audio_piece is None or not getattr(audio_piece, "duration", None) or audio_piece.duration <= 0:
        return video_piece

    factor = (video_piece.duration / audio_piece.duration) if video_piece.duration and audio_piece.duration else 1.0
    r = video_piece.with_effects([vfx.MultiplySpeed(factor)])
    r = r.with_audio(audio_piece)
    return r


def concat(clips: Sequence[Any]) -> Any:
    return concatenate_videoclips(list(clips))
