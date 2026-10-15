"""Рисование отдельным процессом: mflux, Z-Image Turbo.

Отдельный процесс — чтобы 11 ГБ модели уходили из памяти целиком, когда картинка
готова: языковая модель на это время выгружена, вдвоём они в 36 ГБ не помещаются.
Ход — строками в stdout: «step 3/8», «done путь».
"""
import argparse
import sys
import time

SIZES = {"square": (1024, 1024), "portrait": (832, 1216), "landscape": (1216, 832)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("model")
    p.add_argument("prompt")
    p.add_argument("out")
    p.add_argument("--shape", default="square")
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()

    from mflux.models.z_image.variants.z_image import ZImage
    from mflux.models.common.config.model_config import ModelConfig

    print("load", flush=True)
    model = ZImage(model_path=a.model, model_config=ModelConfig.z_image_turbo())
    width, height = SIZES.get(a.shape, SIZES["square"])
    total = a.steps

    class Progress:
        """mflux зовёт обратные вызовы на каждом шаге — по ним и ход."""
        def __init__(self):
            self.n = 0

        def call_in_loop(self, t, seed, prompt, latents, config, time_steps):
            self.n += 1
            print(f"step {min(self.n, total)}/{total}", flush=True)

    model.callbacks.register(Progress())
    seed = a.seed or int(time.time()) % 2_000_000_000
    image = model.generate_image(seed=seed, prompt=a.prompt, num_inference_steps=a.steps,
                                 width=width, height=height)
    image.image.save(a.out)
    print(f"done {a.out}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
