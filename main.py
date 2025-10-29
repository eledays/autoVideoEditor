"""Точка входа: CLI-обёртка над пайплайном обработки видео."""

from __future__ import annotations

import argparse

from src.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Auto Video Editor pipeline")
    p.add_argument("--input", "-i", default="res/Timeline 1.mp4", help="Путь к входному видео")
    p.add_argument("--output", "-o", default="exp.mp4", help="Путь к результату")
    p.add_argument("--threshold", type=float, default=-20.0, help="Порог тишины в dBFS")
    p.add_argument("--min-silence", type=int, default=750, help="Минимальная длительность тишины, мс")
    p.add_argument("--model-path", default="vosk-model", help="Путь к модели Vosk")
    p.add_argument("--sample-rate", type=int, default=16000, help="Частота дискретизации для распознавания")
    p.add_argument("--no-interactive", action="store_true", help="Не спрашивать, какие сегменты удалять")
    p.add_argument("--configure-crop", action="store_true", help="Интерактивная настройка области кропа")
    return p


def main() -> None:
    args = build_parser().parse_args()

    run_pipeline(
        input_path=args.input,
        output_path=args.output,
        silence_threshold_db=args.threshold,
        min_silence_ms=args.min_silence,
        model_path=args.model_path,
        sample_rate=args.sample_rate,
        interactive=not args.no_interactive,
        configure_crop=args.configure_crop,
    )


if __name__ == "__main__":
    main()
