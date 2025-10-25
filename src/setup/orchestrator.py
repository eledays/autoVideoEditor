"""
Оркестратор для процесса настройки проекта.
Координирует установку зависимостей и загрузку моделей.
"""

import sys
import logging
from pathlib import Path
from config import VOSK_MODEL_URL, MODEL_DIR


logger = logging.getLogger(__name__)


def setup_project() -> bool:
    """
    Главная функция настройки проекта.
    Устанавливает все зависимости и загружает необходимые модели.

    Returns:
        bool: True если настройка прошла успешно, False при ошибке
    """
    # Эти импорты будут работать после создания модулей
    try:
        from .package_manager import install_requirements_file
        from .model_downloader import ensure_vosk_model
    except ImportError as e:
        logger.error("Failed to import setup modules: %s", e)
        return False

    project_root = Path(__file__).resolve().parents[2]
    req_file = project_root / "requirements.txt"
    model_dir = project_root / MODEL_DIR
    vosk_url = VOSK_MODEL_URL

    logger.info("Starting project setup...")

    # 1. Установка зависимостей из requirements.txt
    logger.info("Installing Python packages from requirements.txt...")
    if not install_requirements_file(req_file):
        logger.error("Failed to install requirements")
        return False
    logger.info("✓ Python packages installed successfully")

    # 2. Загрузка и установка Vosk модели
    logger.info("Installing Vosk speech recognition model...")
    if not ensure_vosk_model(model_dir, vosk_url, expected_name="vosk-model-ru"):
        logger.error("Failed to install Vosk model")
        return False
    logger.info("✓ Vosk model installed successfully")

    logger.info("🎉 Project setup completed successfully!")
    return True


def main():
    """Точка входа для запуска setup через командную строку."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    success = setup_project()
    if not success:
        logger.error("❌ Setup failed!")
        sys.exit(1)

    logger.info("✅ All done! Your project is ready to use.")


if __name__ == "__main__":
    main()
