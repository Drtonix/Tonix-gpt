"""Чаты: по файлу JSON на чат в Application Support/tonix-gpt/chats.

Картинки пользователя копируются в images рядом: чат не ломается, если
исходный файл переедут или удалят.
"""
import json
import shutil
import time
import uuid
from pathlib import Path

from engine import APP_DIR, IMAGES
from i18n import t as tr

CHATS = APP_DIR / "chats"


def new_chat(model_key):
    return {"id": uuid.uuid4().hex[:12], "title": "", "model": model_key, "created": time.time(),
            "updated": time.time(), "messages": [], "think": False}


def save(chat):
    CHATS.mkdir(parents=True, exist_ok=True)
    chat["updated"] = time.time()
    path = CHATS / f"{chat['id']}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(chat, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def load_all():
    out = []
    if CHATS.exists():
        for f in CHATS.glob("*.json"):
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
    return sorted(out, key=lambda c: c.get("updated", 0), reverse=True)


def delete(chat):
    (CHATS / f"{chat['id']}.json").unlink(missing_ok=True)


def keep_image(src):
    """Копия приложенной картинки в папке приложения."""
    IMAGES.mkdir(parents=True, exist_ok=True)
    src = Path(src)
    dst = IMAGES / f"{uuid.uuid4().hex[:10]}{src.suffix.lower() or '.png'}"
    shutil.copy2(src, dst)
    return str(dst)


def title_from(text):
    t = " ".join((text or "").split())
    return (t[:48] + "…") if len(t) > 48 else (t or tr("Картинка"))
