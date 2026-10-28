from __future__ import annotations

from typing import Any
from pathlib import Path
import json
import tempfile

import pydub
import vosk


class VoskSttService:
    def __init__(self, model_path: str = "vosk-model", sample_rate: int = 16000) -> None:
        self.model_path = model_path
        self.sample_rate = sample_rate
        self._recognizer = vosk.KaldiRecognizer(vosk.Model(model_path), sample_rate)

    def recognize_clip(self, clip: Any) -> str:
        """Extracts audio from the video clip, resamples to 16k mono PCM, and runs Vosk."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_wav = f.name

        try:
            audio = clip.audio
            if audio is None:
                return ""
            audio.write_audiofile(tmp_wav, logger=None)

            seg = pydub.AudioSegment.from_file(tmp_wav)
            seg = seg.set_frame_rate(self.sample_rate).set_channels(1).set_sample_width(2)
            data = seg.raw_data

            self._recognizer.AcceptWaveform(data)
            result = self._recognizer.Result()
            try:
                return json.loads(result).get("text", "").strip()
            except Exception:
                return ""
        finally:
            try:
                Path(tmp_wav).unlink(missing_ok=True)
            except Exception:
                pass
