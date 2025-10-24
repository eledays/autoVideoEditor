import sys
import subprocess
import logging
import shutil
import tempfile
import urllib.request
import zipfile
import time
from pathlib import Path
from importlib import util as importlib_util
from config import VOSK_MODEL_URL, MODEL_DIR
from tqdm import tqdm

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
            logger.warning("pip install failed (attempt %d/%d): %s", attempt, max_retries, e)
            if attempt < max_retries:
                time.sleep(2)
    logger.error("Failed to install %s after %d attempts", package, max_retries)
    return False


def install_requirements_file(req_path: Path) -> bool:
    """Устанавливает зависимости из requirements.txt"""
    if not req_path.exists():
        logger.error("requirements.txt not found: %s", req_path)
        return False
    return pip_install("-r", extra_args=[str(req_path)])


def download_and_extract_zip(url: str, dest_dir: Path, expected_subdir_name: str | None = None, timeout: int = 30) -> bool:
    """
    Скачивает zip в временную папку, распаковывает и атомарно перемещает в dest_dir.
    Если expected_subdir_name указан — проверяет, что распаковка содержит такую папку.
    Показ прогресса скачивания и распаковки через tqdm.
    """
    dest_dir = dest_dir.resolve()
    tmp_dir = Path(tempfile.mkdtemp(prefix="av_editor_"))
    archive_path = tmp_dir / "model.zip"

    try:
        logger.info("Downloading %s → %s", url, archive_path)
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            total = resp.getheader('Content-Length')
            total = int(total) if total and total.isdigit() else None
            with open(archive_path, "wb") as out, tqdm(total=total, unit='B', unit_scale=True, desc='Downloading', leave=True) as pbar:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    out.write(chunk)
                    pbar.update(len(chunk))

        logger.info("Extracting archive to %s", tmp_dir)
        with zipfile.ZipFile(archive_path, "r") as zf:
            members = zf.infolist()
            # Безопасная распаковка с прогрессом (избегаем zip-slip)
            with tqdm(total=len(members), desc='Extracting', unit='file', leave=True) as pbar:
                for member in members:
                    member_path = tmp_dir / member.filename
                    resolved_target = member_path.resolve()
                    if not str(resolved_target).startswith(str(tmp_dir.resolve())):
                        logger.error("Unsafe path in archive: %s", member.filename)
                        return False
                    # Создаём директорию, если нужно
                    if member.is_dir():
                        member_path.mkdir(parents=True, exist_ok=True)
                    else:
                        member_path.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as source, open(member_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                    pbar.update(1)

        # Найдем директорию с моделью
        if expected_subdir_name:
            found = [p for p in tmp_dir.iterdir() if p.is_dir() and expected_subdir_name in p.name]
            if not found:
                logger.error("Expected model folder not found inside archive")
                return False
            model_src = found[0]
        else:
            subs = [p for p in tmp_dir.iterdir() if p.is_dir()]
            if not subs:
                logger.error("No folder found in archive")
                return False
            model_src = subs[0]

        # Атомарное перемещение (удаляем старую папку, если есть)
        if dest_dir.exists():
            logger.info("Removing existing model at %s", dest_dir)
            shutil.rmtree(dest_dir)
        shutil.move(str(model_src), str(dest_dir))
        logger.info("Model installed to %s", dest_dir)
        return True

    except Exception as e:
        logger.error("Failed to download or extract model: %s", e)
        return False
    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass


def ensure_vosk_model(model_dir: Path, url: str, expected_name: str | None = None) -> bool:
    """Проверяет и при необходимости скачивает Vosk модель."""
    model_dir = model_dir.resolve()
    if model_dir.exists() and any(model_dir.iterdir()):
        logger.info("Vosk model exists at %s", model_dir)
        return True

    logger.info("Vosk model not found at %s; attempting download", model_dir)
    model_dir.parent.mkdir(parents=True, exist_ok=True)
    return download_and_extract_zip(url, model_dir, expected_subdir_name=expected_name)


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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    project_root = Path(__file__).resolve().parents[2]
    req_file = project_root / "requirements.txt"
    model_dir = project_root / MODEL_DIR
    vosk_url = VOSK_MODEL_URL

    ok = install_requirements_file(req_file)
    if not ok:
        logger.error("Failed to install requirements")
        sys.exit(2)

    if not ensure_vosk_model(model_dir, vosk_url, expected_name="vosk-model-ru"):
        logger.error("Failed to install Vosk model")
        sys.exit(3)

    logger.info("Setup finished successfully")
