from __future__ import annotations

from typing import List, Tuple, Optional
import logging

from moviepy import VideoFileClip

from src.domain.entities import TranscriptSegment
from src.services.audio_service import find_silence, get_non_silences
from src.services.stt_service import VoskSttService
from src.services.video_service import split_to_clips, speed_up_segment, concat
from src.services.layout_service import compose_vertical
from src.services.preview_service import configure_crop_interactive, get_default_crop_for_vertical


def run_pipeline(
    input_path: str,
    output_path: str = "exp.mp4",
    *,
    silence_threshold_db: float = -20.0,
    min_silence_ms: int = 750,
    model_path: str = "vosk-model",
    sample_rate: int = 16000,
    interactive: bool = True,
    configure_crop: bool = False,
    bg_color: Tuple[int, int, int] = (28, 31, 32),
    out_size: Tuple[int, int] = (1080, 1920),
    crop_box: Optional[Tuple[int, int, int, int]] = None,
    scale: float = 1.25,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    logger = logging.getLogger(__name__)

    logger.info("Загрузка видео: %s", input_path)
    video = VideoFileClip(input_path)

    try:
        # Настройка кропа, если требуется
        final_crop_box = crop_box
        if configure_crop:
            logger.info("Настройка области кропа...")
            final_crop_box = configure_crop_interactive(video, time_seconds=10.0)
            logger.info("Выбран кроп: %s", final_crop_box)
        elif crop_box is None:
            # Автоматический кроп для вертикального видео
            final_crop_box = get_default_crop_for_vertical(video.w, video.h)
            logger.info("Авто-кроп для вертикального видео: %s", final_crop_box)
        logger.info("Детекция тишины...")
        silences = find_silence(video, silence_threshold_db, min_silence_ms)
        logger.info("Тишин найдено: %d", len(silences))

        logger.info("Формирование non-silence сегментов...")
        non_silences = get_non_silences(silences, total_duration=video.duration)
        logger.info("Сегментов речи: %d", len(non_silences))

        if not non_silences:
            logger.warning("Не найдено сегментов речи — экспорт исходника.")
            video.write_videofile(output_path)
            return

        logger.info("Нарезка видео по сегментам речи...")
        clips = split_to_clips(video, non_silences)

        logger.info("Инициализация Vosk: %s", model_path)
        stt = VoskSttService(model_path=model_path, sample_rate=sample_rate)

        logger.info("Распознавание текста для каждого клипа...")
        transcripts: List[TranscriptSegment] = []
        for i, clip in enumerate(clips):
            text = stt.recognize_clip(clip)
            transcripts.append(TranscriptSegment(start=non_silences[i].start, end=non_silences[i].end, text=text))
            logger.info("%d. %.2f-%.2f: %s", i + 1, non_silences[i].start, non_silences[i].end, text)

        if interactive:
            print("\nУдалить (номера через пробел, 1..N). Пусто — ничего: ", end="")
            raw = input().strip()
            if raw:
                indices = sorted({int(x) - 1 for x in raw.split() if x.isdigit()}, reverse=True)
                for idx in indices:
                    if 0 <= idx < len(clips):
                        clips.pop(idx)
                        non_silences.pop(idx)

        logger.info("Ускоряем и согласуем фрагменты...")
        result_parts = [speed_up_segment(video, clip, non_silences, i) for i, clip in enumerate(clips)]

        if not result_parts:
            logger.warning("После удаления не осталось клипов — сохраняем исходник.")
            video.write_videofile(output_path)
            return

        logger.info("Склейка клипов...")
        merged = concat(result_parts)

        logger.info("Компоновка вертикального видео...")
        # final_crop_box гарантированно не None после инициализации выше
        assert final_crop_box is not None
        composed = compose_vertical(merged, bg_color=bg_color, out_size=out_size, crop_box=final_crop_box, scale=scale)

        logger.info("Экспорт: %s", output_path)
        composed.write_videofile(output_path)
    finally:
        try:
            video.close()
        except Exception:
            pass
