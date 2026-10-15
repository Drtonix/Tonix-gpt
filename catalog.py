"""Модели tonix-gpt: что есть и сколько весит. Где лежат и как качаются —
общее для всех приложений хранилище models_home.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Model:
    key: str
    title: str
    repo: str
    size_gb: float              # ГиБ, как показывают остальные приложения
    vision: bool
    kind: str = "chat"          # chat — собеседник, image — рисование
    free: bool = False          # без ограничений (abliterated)


MODELS = [
    Model("qwen", "Qwen 3.6", "mlx-community/Qwen3.6-35B-A3B-4bit", 19.0, True),
    Model("huihui-qwen", "Qwen 3.6 · huihui", "vanch007/Huihui-Qwen3.6-35B-A3B-abliterated-mlx-4bit", 19.0, True, free=True),
    Model("gemma", "Gemma 4", "mlx-community/gemma-4-26B-A4B-it-qat-4bit", 14.6, True),
    Model("huihui-gemma", "Gemma 4 · huihui", "vanch007/Huihui-gemma-4-26B-A4B-it-abliterated-mlx-4bit", 14.6, True, free=True),
    Model("qwen-dense", "Qwen 3.8 27B", "mlx-community/Qwen3.8-27B-4bit", 15.0, True),
    Model("qwen3", "Qwen 3 30B", "mlx-community/Qwen3-30B-A3B-4bit", 16.0, False),
    Model("qwen3-32b", "Qwen 3 32B", "mlx-community/Qwen3-32B-4bit-DWQ", 17.2, False),
    Model("qwen3-8b", "Qwen 3 8B", "mlx-community/Qwen3-8B-4bit", 4.3, False),
    Model("gpt-oss", "gpt-oss 20B", "mlx-community/gpt-oss-20b-MXFP4-Q8", 11.3, False),
    Model("z-image", "Z-Image Turbo", "mflux-community/z-image-turbo-mflux-q8", 10.2, False, kind="image"),
]
BY_KEY = {m.key: m for m in MODELS}


import models_home as home  # noqa: E402

folder = home.folder
set_folder = home.set_folder
volume_of = home.volume_of
mounted = home.mounted


def local_path(model):
    return home.resolve(model.repo)


def state(model):
    return home.state(model.repo)


def where(model):
    return home.where(model.repo)


def shared(model):
    return home.shared(model.repo)


def installed(model):
    return home.resolve(model.repo) is not None


def target(model):
    return home.target(model.repo)


def downloaded_bytes(model):
    return home.on_disk(model.repo)


def download(model):
    """В общую очередь: качает загрузчик, ход видно в окне «Модели»."""
    home.enqueue(model.repo)


def cancel(model):
    home.cancel(model.repo)


def remove(model):
    home.remove(model.repo)
