from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    start: float  # seconds
    end: float    # seconds


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
