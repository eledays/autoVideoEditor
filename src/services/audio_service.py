from __future__ import annotations

from typing import List, Sequence, Optional, Any
from pathlib import Path
import tempfile

import pydub

from src.domain.entities import Segment


def find_silence(
    video: Any,
    silence_threshold_db: float = -20.0,
    min_silence_ms: int = 750,
) -> List[Segment]:
    """Detect silence intervals in a video's audio track by dBFS.
    Writes audio to a temporary wav, iterates per-ms similar to prototype.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_wav = f.name

    try:
        if getattr(video, "audio", None) is None:
            return []
        video.audio.write_audiofile(tmp_wav, logger=None)
        audio = pydub.AudioSegment.from_file(tmp_wav)

        starts: List[int] = []
        ends: List[int] = []
        current_start: Optional[int] = None

        for i in range(len(audio)):
            if audio[i].dBFS < silence_threshold_db and current_start is None:
                current_start = i
            elif audio[i].dBFS >= silence_threshold_db:
                if current_start is not None and (i - current_start) > min_silence_ms:
                    starts.append(current_start)
                    ends.append(i)
                current_start = None

        if current_start is not None:
            starts.append(current_start)
            ends.append(len(audio))

        raw = [(start / 1000.0, end / 1000.0) for start, end in zip(starts, ends)]
        if raw and raw[0][0] == 0:
            raw = raw[1:]

        return [Segment(s, e) for s, e in raw]
    finally:
        try:
            Path(tmp_wav).unlink(missing_ok=True)
        except Exception:
            pass


def get_non_silences(silences: Sequence[Segment], total_duration: float) -> List[Segment]:
    r: List[Segment] = []
    last = 0.0

    for seg in silences:
        if seg.start > last:
            r.append(Segment(last, seg.start))
        last = seg.end

    if last < total_duration:
        r.append(Segment(last, total_duration))

    return [s for s in r if s.end - s.start > 1e-3]
