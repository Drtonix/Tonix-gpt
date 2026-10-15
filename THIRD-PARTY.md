# Third-party components

The MIT license in `LICENSE` covers the code in this repository only. The
distributed `.app` bundle also contains the components below. Their full
license texts are inside the bundle, in `Contents/Resources/Лицензии`.

## Bundled in the application

| Component | Version | License | Source |
|---|---|---|---|
| Qt (via PySide6) | 6.12.0 | LGPL-3.0 | https://download.qt.io/official_releases/QtForPython/ |
| CPython | 3.12.14 | PSF-2.0 | https://github.com/astral-sh/python-build-standalone |
| MLX, mlx-lm, mlx-vlm | 0.32.3 / 0.32.0 / 0.7.6 | MIT | https://github.com/ml-explore/mlx |
| mflux | 0.22.0 | MIT | https://github.com/filipstrand/mflux |
| Transformers, huggingface-hub | 5.19.0 / 1.33.0 | Apache-2.0 | https://github.com/huggingface/transformers |
| PyTorch | 2.14.1 | BSD-3-Clause | https://github.com/pytorch/pytorch |
| trafilatura | 2.3.1 | Apache-2.0 | https://github.com/adbar/trafilatura |
| Pillow | 12.3.0 | MIT-CMU | https://github.com/python-pillow/Pillow |
| Markdown | 3.11 | BSD-3-Clause | https://github.com/Python-Markdown/markdown |
| NumPy | 2.5.3 | BSD-3-Clause | https://numpy.org |
| truststore, certifi | 0.10.4 / 2026.7.22 | MIT / MPL-2.0 | https://github.com/sethmlarson/truststore |

Qt is dynamically linked. To relink the application against your own build,
replace the libraries in
`tonix-gpt.app/Contents/Resources/python/lib/python3.12/site-packages/PySide6`.

`certs/russian-trusted-ca.pem` is the public Russian Trusted Root CA
certificate from gu-st.ru, used only when a site fails the normal check.

## Neural network weights

Downloaded from Settings and not redistributed:

| Model | License | Source |
|---|---|---|
| Qwen 3.6, Qwen 3.8, Qwen 3 | Apache-2.0 | https://huggingface.co/Qwen |
| Gemma 4 | Gemma Terms of Use | https://huggingface.co/google |
| gpt-oss 20B | Apache-2.0 | https://huggingface.co/openai/gpt-oss-20b |
| huihui builds of Qwen 3.6 and Gemma 4 | as the base model | https://huggingface.co/huihui-ai |
| Z-Image Turbo | Apache-2.0 | https://huggingface.co/Tongyi-MAI/Z-Image-Turbo |
