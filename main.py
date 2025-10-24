import os
import sys
import logging

# Проверяем и устанавливаем зависимости при первом запуске
def check_dependencies():
    """Проверяет наличие зависимостей и предлагает их установить"""
    missing_deps = []
    
    try:
        import pydub
    except ImportError:
        missing_deps.append("pydub")
    
    try:
        from moviepy import VideoFileClip
    except ImportError:
        missing_deps.append("moviepy")
    
    try:
        import vosk
    except ImportError:
        missing_deps.append("vosk")
    
    # Проверяем наличие модели Vosk
    if not os.path.exists("vosk-model") or not os.listdir("vosk-model"):
        missing_deps.append("vosk-model")
    
    if missing_deps:
        print("❌ Обнаружены недостающие зависимости:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print()
        print("🛠️  Для автоматической установки запустите:")
        print("   python auto_setup.py")
        print()
        print("📚 Или установите вручную:")
        print("   pip install -r requirements.txt")
        if "vosk-model" in missing_deps:
            print("   и скачайте модель Vosk из https://alphacephei.com/vosk/models/")
        
        sys.exit(1)

# Проверяем зависимости перед импортом
check_dependencies()

import pydub
from moviepy import VideoFileClip, CompositeVideoClip, ColorClip, concatenate_videoclips, vfx
import vosk
import json


def find_silence(video, silence_threshold=-20, mn_silence_duration=750):
    file_name = 'res/audio.wav'
    video.audio.write_audiofile(file_name, logger=None)
    audio = pydub.AudioSegment.from_file(file_name)

    starts = []
    ends = []

    current_start = None

    for i in range(len(audio)):
        if audio[i].dBFS < silence_threshold and current_start is None:
            current_start = i
        elif audio[i].dBFS >= silence_threshold:
            if current_start is not None and i - current_start > mn_silence_duration:
                starts.append(current_start)
                ends.append(i)
            current_start = None

    if current_start is not None:
        starts.append(current_start)
        ends.append(len(audio))

    r = [(start / 1000, end / 1000) for start, end in zip(starts, ends)]

    if r[0][0] == 0:
        r = r[1:]

    return r


def get_non_silences(silences):
    r = []

    last = 0
    for start, end in silences:
        r.append((last, start))
        last = end

    return r


def split_to_clips(video, non_silences):
    clips = []

    for start, end in non_silences:
        dl = .3
        start -= dl if start - dl >= 0 else 0
        end += dl
        clips.append(video.subclip(start, end))

    return clips


def recognize_text(clip):
    file_name = 'res/audio_piece.wav'

    audio = clip.audio
    audio.write_audiofile(file_name, logger=None)

    audio = pydub.AudioSegment.from_file(file_name)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    data = audio.raw_data

    rec.AcceptWaveform(data)
    result = rec.Result()

    return json.loads(result)['text']


def speed_up(video, clip, non_silences, i):
    start = non_silences[i][1]
    end = non_silences[i + 1][0] if i + 1 < len(clips) else None

    video_piece = video.subclip(start, end).without_audio()
    audio_piece = clip.audio

    r = video_piece.with_effects([vfx.MultiplySpeed(video_piece.duration / audio_piece.duration)])
    r = r.with_audio(audio_piece)

    return r


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

logger = logging.getLogger(__name__)


# объявляем переменные
video = VideoFileClip('res/Timeline 1.mp4')
rec = vosk.KaldiRecognizer(vosk.Model('vosk-model'), 16000)


# получаем кусочки и разбиваем видео
silences = find_silence(video)
non_silences = get_non_silences(silences)
clips = split_to_clips(video, non_silences)


# выводим текст кусков
for i, clip in enumerate(clips):
    text = recognize_text(clip)
    start, end = non_silences[i]

    print(f'{i + 1}. {start}-{end}: {text}')


# удалением лишнее
ns = sorted(list(map(lambda x: int(x) - 1, input('Удалить: ').split())), reverse=True)
[clips.pop(i) for i in ns]
[non_silences.pop(i) for i in ns]


# ускоряем
result = [speed_up(video, clip, non_silences, i) for i, clip in enumerate(clips)]


# собираем
video = concatenate_videoclips(result)


# создаем фон
video = video.resized(1.25)
left_part = video.with_effects([vfx.Crop(x1=0, y1=0, x2=1080, y2=1440)])
background = ColorClip((1080, 1920), color=(28, 31, 32), duration=video.duration)
final_video = CompositeVideoClip([background, left_part.with_position(("center", "center"))])


final_video.write_videofile('exp.mp4')
