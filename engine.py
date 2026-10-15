"""Разговор: сервер mlx-vlm отдельным процессом и цикл с инструментами.

Сервер держит одну модель и сам грузит нужную по первому запросу; шаблоны чата,
разбор вызовов инструментов и отделение размышлений — его (форматы Qwen,
Gemma 4 и harmony у gpt-oss он знает). Отдельный процесс ещё и потому, что
перед рисованием модель выгружается целиком — 20 ГБ и 11 ГБ вместе в 36 ГБ
не помещаются.
"""
import base64
import datetime
import json
import mimetypes
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import catalog
import tools
from i18n import MONTHS, WEEKDAYS, current, t, tf

HERE = Path(__file__).resolve().parent
# TONIX_GPT_DATA — для проверок: чаты и картинки не в папку пользователя.
APP_DIR = Path(os.environ.get("TONIX_GPT_DATA") or Path.home() / "Library" / "Application Support" / "tonix-gpt")
IMAGES = APP_DIR / "images"
MAX_ROUNDS = 8                  # столько раз подряд модель может звать инструменты

# Запросы к своему серверу — мимо системного прокси (как в Dubl).
_local = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Server:
    def __init__(self):
        import threading
        self.proc = None
        self.port = None
        self.log = None
        self.ready = False
        # Прогрев (пока человек печатает) и сам ответ запускают сервер из разных
        # потоков: второй ждёт, пока первый дождётся ответа сервера.
        self.lock = threading.Lock()

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, wait=90):
        with self.lock:
            if self.alive() and self.ready:
                return
            self._start(wait)

    def _start(self, wait):
        if self.alive():
            self.stop()
        self.ready = False
        APP_DIR.mkdir(parents=True, exist_ok=True)
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        env = dict(os.environ, HF_HUB_OFFLINE="1", HF_HUB_DISABLE_XET="1", TOKENIZERS_PARALLELISM="false")
        self.log = open(APP_DIR / "server.log", "w")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "mlx_vlm.server", "--host", "127.0.0.1", "--port", str(self.port),
             "--log-level", "WARNING", "--max-tokens", "8192"],
            stdout=self.log, stderr=subprocess.STDOUT, env=env, cwd=str(APP_DIR))
        until = time.time() + wait
        while time.time() < until:
            if self.proc.poll() is not None:
                raise RuntimeError(t("сервер моделей не запустился — подробности в server.log"))
            try:
                _local.open(f"http://127.0.0.1:{self.port}/health", timeout=2).read()
                self.ready = True
                return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError(t("сервер моделей не отвечает"))

    def unload(self):
        if self.alive():
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{self.port}/unload", data=b"{}",
                                             headers={"Content-Type": "application/json"})
                _local.open(req, timeout=30).read()
            except Exception:
                pass

    def stop(self):
        self.ready = False
        if self.alive():
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def stream(self, body, stop=None):
        """Поток ответа: словари delta из событий SSE."""
        self.start()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/chat/completions",
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with _local.open(req, timeout=900) as r:
            for raw in r:
                if stop and stop():
                    return
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                chunk = json.loads(data)
                if chunk.get("error"):
                    raise RuntimeError(chunk["error"].get("message", t("ошибка модели")))
                choice = (chunk.get("choices") or [{}])[0]
                yield choice.get("delta") or {}, choice.get("finish_reason")


def system_prompt(web, draw):
    now = datetime.datetime.now()
    lang = current()
    month, day = MONTHS[lang][now.month - 1], WEEKDAYS[lang][now.weekday()]
    date = (f"{now.day} {month} {now.year}" if lang == "ru" else f"{month} {now.day}, {now.year}")
    lines = [t("Ты — собеседник в приложении tonix-gpt на компьютере пользователя. "
               "Отвечай на языке, на котором пишут тебе. Оформляй ответ Markdown, когда это помогает."),
             tf("Сейчас {date}.", date=f"{date}, {day}, {now:%H:%M}")]
    if web:
        lines.append(t("У тебя есть интернет: web_search ищет, open_url читает страницу. Ищи, когда нужны "
                       "свежие данные — новости, цены, погода, расписания, — или когда не уверен в факте. "
                       "Цифры и факты бери только из найденного: если в выдержках поиска нужного нет, открой "
                       "страницу через open_url. Источник называй ссылкой на ту страницу, откуда взял, — "
                       "не придумывай источники, которых не открывал и не видел в выдаче."))
    else:
        lines.append(t("Интернета у тебя сейчас нет: о свежих событиях можешь не знать — так и скажи."))
    if draw:
        lines.append(t("generate_image рисует картинку по описанию: зови его, когда просят нарисовать "
                       "или показать что-то картинкой. Описание пиши подробно и по-английски."))
    return "\n".join(lines)


def image_part(path):
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    data = base64.b64encode(Path(path).read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}


def api_messages(chat, model, web, draw):
    """История чата → сообщения OpenAI. Картинки — только моделям со зрением."""
    out = [{"role": "system", "content": system_prompt(web, draw)}]
    for m in chat["messages"]:
        if m["role"] == "user":
            pics = [p for p in m.get("images", []) if Path(p).exists()]
            if pics and model.vision:
                content = [{"type": "text", "text": m["text"] or t("Что на картинке?")}]
                content += [image_part(p) for p in pics]
                out.append({"role": "user", "content": content})
            else:
                note = tf("\n\n[приложено картинок: {n} — эта модель их не видит]", n=len(pics)) if pics else ""
                out.append({"role": "user", "content": (m["text"] or "") + note})
        else:
            out.extend(m.get("api", []))
    return out


def run_turn(server, chat, model, web, draw, emit, stop):
    """Ответ модели на последнее сообщение, с инструментами.
    emit(событие, данные): status, reasoning, text, tool_start, tool_progress, tool_done.
    → запись для истории: части для показа и сообщения OpenAI для следующего хода."""
    schemas = [s for s in tools.schemas()
               if (web and s["function"]["name"] in ("web_search", "open_url"))
               or (draw and s["function"]["name"] == "generate_image")]
    messages = api_messages(chat, model, web, draw)
    path = model_path(model)
    turn_api, parts = [], []
    seen, stuck = set(), False
    started = time.time()
    for round_ in range(MAX_ROUNDS):
        # Последний круг — или модель пошла по кругу одними и теми же запросами:
        # отвечать по найденному, без инструментов.
        final = bool(schemas) and (stuck or round_ == MAX_ROUNDS - 1)
        if final:
            body = {"model": path, "messages": _final_messages(messages, parts),
                    "stream": True, "max_tokens": 8192}
        else:
            body = {"model": path, "messages": messages + turn_api, "stream": True, "max_tokens": 8192}
            if schemas:
                body["tools"] = schemas
        if chat.get("think") is not None:
            body["enable_thinking"] = bool(chat["think"])
        body.update(sampling(model, bool(chat.get("think"))))
        emit("status", t("Загрузка модели…") if not server_loaded(server, path) else t("Ответ…"))
        text, reasoning, calls = "", "", {}
        junk = _ChannelJunk()
        for delta, finish in server.stream(body, stop):
            r = delta.get("reasoning_content") or delta.get("reasoning") or ""
            if r:
                reasoning += r
                emit("reasoning", r)
            c = junk.feed(delta.get("content") or "")
            if c:
                text += c
                emit("text", c)
                cut = looping(text)
                if cut:
                    # Модель застряла на одном куске — дальше будет только он.
                    text = text[:-cut].rstrip()
                    emit("replace", text)
                    break
            for tc in delta.get("tool_calls") or []:
                slot = calls.setdefault(tc.get("index", len(calls)), {"id": tc.get("id"), "name": "", "args": ""})
                f = tc.get("function") or {}
                slot["id"] = slot["id"] or tc.get("id")
                slot["name"] += f.get("name") or ""
                a = f.get("arguments")
                slot["args"] += a if isinstance(a, str) else json.dumps(a or {}, ensure_ascii=False)
        tail = junk.flush()
        if tail:
            text += tail
            emit("text", tail)
        if stop():
            break
        if reasoning:
            parts.append({"kind": "reasoning", "text": reasoning})
        if text:
            parts.append({"kind": "text", "text": text})
        msg = {"role": "assistant", "content": text}
        if reasoning:
            msg["reasoning_content"] = reasoning
        if final or not calls:
            turn_api.append(msg)
            break
        msg["tool_calls"] = [{"id": c["id"] or f"call_{i}", "type": "function",
                              "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
                             for i, c in sorted(calls.items())]
        turn_api.append(msg)
        fresh = 0
        for i, c in sorted(calls.items()):
            try:
                args = json.loads(c["args"] or "{}")
            except ValueError:
                args = {}
            key = (c["name"], json.dumps(args, sort_keys=True, ensure_ascii=False))
            if key in seen:
                result = t("Этот запрос уже был — результаты выше.")
            else:
                seen.add(key)
                fresh += 1
                part = run_tool(server, c["name"], args, emit, stop)
                parts.append(part)
                result = part["result"]
            turn_api.append({"role": "tool", "tool_call_id": c["id"] or f"call_{i}", "content": result})
        stuck = fresh == 0
    return {"role": "assistant", "parts": parts, "api": turn_api, "model": model.key,
            "seconds": round(time.time() - started, 1)}


class _ChannelJunk:
    """Gemma 4 порой роняет в ответ обрывок служебной метки размышлений
    («-<|channel>…»): целую метку сервер вырезает сам, обрывок — нет.
    Вырезаем его из потока до конца строки или до закрывающей метки."""
    OPEN, CLOSE = "<|channel>", "<channel|>"

    def __init__(self):
        self.buf = ""

    def feed(self, chunk):
        self.buf += chunk
        out = ""
        while True:
            i = self.buf.find(self.OPEN)
            if i < 0:
                keep = self._tail(self.buf)
                out += self.buf[:len(self.buf) - keep]
                self.buf = self.buf[len(self.buf) - keep:]
                return out
            start = i - 1 if i and self.buf[i - 1] == "-" else i
            out += self.buf[:start]
            nl, close = self.buf.find("\n", i), self.buf.find(self.CLOSE, i)
            ends = [e for e in (nl + 1 if nl >= 0 else 0, close + len(self.CLOSE) if close >= 0 else 0) if e]
            if not ends:
                self.buf = self.buf[start:]
                return out
            self.buf = self.buf[min(ends):]

    def flush(self):
        rest, self.buf = self.buf, ""
        i = rest.find(self.OPEN)
        if i >= 0:
            return rest[:i - 1 if i and rest[i - 1] == "-" else i]
        keep = self._tail(rest)
        return rest[:len(rest) - keep] if "<|" in rest[len(rest) - keep:] else rest

    def _tail(self, s):
        """Сколько символов в конце может оказаться началом метки — их придержать."""
        for marker in ("-" + self.OPEN, self.OPEN):
            for n in range(min(len(marker) - 1, len(s)), 0, -1):
                if s.endswith(marker[:n]):
                    return n
        return 0


def sampling(model, think):
    """Настройки выборки слов, рекомендованные разработчиками моделей. Без них
    сервер берёт всегда самое вероятное слово, и модели — особенно huihui —
    застревают на одном куске. Зерно своё у каждого ответа."""
    import random
    repo = model.repo.lower()
    if "gemma" in repo:
        out = {"temperature": 1.0, "top_p": 0.95, "top_k": 64}
    elif "gpt-oss" in repo:
        out = {"temperature": 1.0, "top_p": 1.0}
    elif think:
        out = {"temperature": 0.6, "top_p": 0.95, "top_k": 20}
    else:
        out = {"temperature": 0.7, "top_p": 0.8, "top_k": 20}
    out["repetition_penalty"] = 1.1 if model.free else 1.03
    out["repetition_context_size"] = 256
    out["seed"] = random.randrange(1 << 31)
    return out


def looping(text):
    """Сколько символов в конце — повтор одного куска («set_set_set…»): кусок
    от 1 до 40 знаков, подряд не меньше 6 раз и не меньше 80 знаков. 0 — повтора нет."""
    tail = text[-480:]
    for n in range(1, 41):
        unit = tail[-n:]
        if len(unit) < n or not unit.strip():
            continue
        reps, i = 1, len(tail) - 2 * n
        while i >= 0 and tail[i:i + n] == unit:
            reps += 1
            i -= n
        if reps >= 6 and reps * n >= 80:
            return n * (reps - 1)
    return 0


def _final_messages(messages, parts):
    """Найденное — прямо в вопрос, без истории вызовов: с ней модель, привыкшая
    искать, и без инструментов пишет текстом очередной запрос."""
    found, size = [], 0
    for p in parts:
        r = (p.get("result") or "")[:5000]
        if p.get("kind") == "tool" and r and size + len(r) <= 30000:
            found.append(r)
            size += len(r)
    note = (t("\n\nНайдено в интернете:\n\n") + "\n\n".join(found) if found else "")
    note += t("\n\nПоиск закончен. Ответь на вопрос по найденному, без новых запросов.")
    out = list(messages)
    last = dict(out[-1])
    if isinstance(last["content"], list):
        last["content"] = last["content"] + [{"type": "text", "text": note}]
    else:
        last["content"] = (last["content"] or "") + note
    out[-1] = last
    return out


_loaded = {"repo": None}


def model_path(model):
    """Модель серверу отдаётся папкой: так она грузится из любой папки моделей."""
    path = catalog.local_path(model)
    if path is None:
        if catalog.state(model) == "offline":
            raise RuntimeError(tf("{name} лежит в {where}, папка недоступна",
                                  name=model.title, where=catalog.where(model)))
        raise RuntimeError(tf("{name} не скачана — она в «Настройках»", name=model.title))
    return str(path)


def server_loaded(server, path):
    """Загружена ли эта модель — по последнему запросу: сервер держит одну."""
    was = _loaded["repo"] == path and server.alive()
    _loaded["repo"] = path
    return was


def run_tool(server, name, args, emit, stop):
    emit("tool_start", {"name": name, "args": args})
    part = {"kind": "tool", "name": name, "args": args}
    try:
        if name == "web_search":
            q = str(args.get("query", "")).strip()
            text, found = tools.web_search(q)
            part.update(summary=tf("Поиск: «{q}»", q=q), links=found[:6], result=text)
        elif name == "open_url":
            url = str(args.get("url", "")).strip()
            text = tools.open_url(url)
            part.update(summary=t("Страница: ") + url.split("//")[-1].split("/")[0], links=[{"url": url, "title": url}],
                        result=text)
        elif name == "generate_image":
            path = draw(server, str(args.get("prompt", "")), str(args.get("shape", "square")), emit, stop)
            part.update(summary=t("Рисунок"), images=[str(path)], prompt=args.get("prompt", ""),
                        result=t("Картинка нарисована и уже показана пользователю. Коротко скажи, что получилось."))
        else:
            part.update(summary=name, result=tf("Инструмента {name} нет.", name=name))
    except Exception as e:
        part.update(summary=part.get("summary") or name, error=str(e)[:300],
                    result=tf("Не вышло: {e}", e=str(e)[:300]))
    emit("tool_done", part)
    return part


def draw(server, prompt, shape, emit, stop):
    path = model_path(catalog.BY_KEY["z-image"])
    # Языковую модель — из памяти: вдвоём они не помещаются. Следующий запрос
    # сервер загрузит её заново сам (из кэша диска — секунды).
    emit("tool_progress", (t("Освобождение памяти…"), None))
    server.unload()
    _loaded["repo"] = None
    IMAGES.mkdir(parents=True, exist_ok=True)
    out = IMAGES / f"{datetime.datetime.now():%Y-%m-%d %H-%M-%S}.png"
    env = dict(os.environ, HF_HUB_OFFLINE="1")
    proc = subprocess.Popen([sys.executable, str(HERE / "imagegen.py"), str(path), prompt, str(out),
                             "--shape", shape], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=env)
    for line in proc.stdout:
        if stop():
            proc.kill()
            raise RuntimeError(t("остановлено"))
        line = line.strip()
        if line == "load":
            emit("tool_progress", (t("Загрузка модели рисования…"), None))
        elif line.startswith("step "):
            n, total = map(int, line.split()[1].split("/"))
            emit("tool_progress", (tf("Рисование · шаг {n} из {total}", n=n, total=total), n / total))
    proc.wait()
    if proc.returncode != 0 or not out.exists():
        tail = [x for x in proc.stderr.read().splitlines() if x.strip()]
        raise RuntimeError(tail[-1] if tail else t("не нарисовалось"))
    return out
