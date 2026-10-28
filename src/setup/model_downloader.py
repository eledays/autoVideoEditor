import shutil
import tempfile
import urllib.request
import zipfile
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def download_and_extract_zip(url: str, dest_dir: Path, expected_subdir_name: str | None = None, timeout: int = 30) -> bool:
    """
    Скачивает zip в временную папку, распаковывает и атомарно перемещает в dest_dir.
    Если expected_subdir_name указан — проверяет, что распаковка содержит такую папку.
    Показ прогресса скачивания и распаковки через tqdm.
    """
    from tqdm import tqdm

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
                        logger.error("Unsafe path in archive: %s",
                                     member.filename)
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
            found = [p for p in tmp_dir.iterdir() if p.is_dir()
                     and expected_subdir_name in p.name]
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
