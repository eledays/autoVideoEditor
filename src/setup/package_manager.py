import sys
import subprocess
import logging
import time
from pathlib import Path
from importlib import util as importlib_util
from config import VOSK_MODEL_URL, MODEL_DIR


logger = logging.getLogger(__name__)


def is_package_installed(module_name: str) -> bool:
    """Проверяет, можно ли импортировать модуль"""
    return importlib_util.find_spec(module_name) is not None


def pip_install(package: str, max_retries: int = 2, extra_args: list | None = None) -> bool:
    """Устанавливает пакет через pip (sys.executable -m pip). Возвращает True при успехе."""
    args = [sys.executable, "-m", "pip", "install", package]
    if extra_args:
        args.extend(extra_args)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Running: %s", " ".join(args))
            subprocess.check_call(args)
            return True
        except subprocess.CalledProcessError as e:
            logger.warning("pip install failed (attempt %d/%d): %s",
                           attempt, max_retries, e)
            if attempt < max_retries:
                time.sleep(2)
    logger.error("Failed to install %s after %d attempts",
                 package, max_retries)
    return False


def install_requirements_file(req_path: Path) -> bool:
    """Устанавливает зависимости из requirements.txt"""
    if not req_path.exists():
        logger.error("requirements.txt not found: %s", req_path)
        return False
    return pip_install("-r", extra_args=[str(req_path)])


def install_missing_packages(packages: dict) -> bool:
    """
    packages: mapping package_name -> import_name (import_name optional)
    вернёт True если все установлены/установлены успешно
    """
    all_ok = True
    for pkg, import_name in packages.items():
        mod = import_name or pkg
        if is_package_installed(mod):
            logger.info("%s already available", pkg)
            continue
        logger.info("%s is missing — installing", pkg)
        ok = pip_install(pkg)
        if not ok:
            all_ok = False
    return all_ok
