"""Инструменты чат-бота: поиск в интернете, чтение страницы, рисование.

Поиск — HTML-выдача DuckDuckGo обычным запросом, без подделки под браузер;
не ответил — Википедия через её API. Страница — своя загрузка и разбор
trafilatura (его собственная загрузка на кириллических адресах молчит).
"""
import gzip
import html
import json
import re
import ssl
import zlib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from i18n import current, t, tf

UA = "tonix-gpt/1.0 (+https://bdub.space)"
# Часть российских сайтов (cbr.ru, госуслуги) подписана «Russian Trusted Root CA»,
# которого нет ни в macOS, ни в Python. Корень скачан с gu-st.ru и включается,
# только если обычная проверка не прошла.
RU_CA = Path(__file__).resolve().parent / "certs" / "russian-trusted-ca.pem"


def _contexts():
    import certifi
    import truststore
    yield truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx = ssl.create_default_context(cafile=certifi.where())
    if RU_CA.exists():
        ctx.load_verify_locations(cafile=str(RU_CA))
    yield ctx


def _iri(url):
    """Адрес с кириллицей — в вид, который принимает urllib."""
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname.encode("idna").decode() if parts.hostname else ""
    netloc = host + (f":{parts.port}" if parts.port else "")
    return urllib.parse.urlunsplit((parts.scheme, netloc,
                                    urllib.parse.quote(parts.path, safe="/%:@!$&'()*+,;="),
                                    urllib.parse.quote(parts.query, safe="=&%+/:@!$'()*,;?"),
                                    ""))
PAGE_LIMIT = 12000      # столько символов страницы уходит модели


def schemas():
    """Описания инструментов на языке интерфейса."""
    return [
        {"type": "function", "function": {
            "name": "web_search",
            "description": t("Поиск в интернете. Возвращает заголовки, адреса и короткие выдержки. "
                             "Для свежих новостей, цен, погоды, фактов, которых модель может не знать."),
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": t("Поисковый запрос")}},
                "required": ["query"]}}},
        {"type": "function", "function": {
            "name": "open_url",
            "description": t("Открыть страницу по адресу и прочитать её текст."),
            "parameters": {"type": "object", "properties": {
                "url": {"type": "string", "description": t("Адрес страницы")}},
                "required": ["url"]}}},
        {"type": "function", "function": {
            "name": "generate_image",
            "description": t("Нарисовать картинку по описанию. Описание — подробное, лучше по-английски: "
                             "что изображено, стиль, свет, ракурс."),
            "parameters": {"type": "object", "properties": {
                "prompt": {"type": "string", "description": t("Описание картинки")},
                "shape": {"type": "string", "enum": ["square", "portrait", "landscape"],
                          "description": t("Формат: квадрат, вертикальная или горизонтальная")}},
                "required": ["prompt"]}}},
    ]


def _unpack(body, headers):
    """Часть сайтов (python.org) жмёт ответ, даже когда сжатия не просили."""
    enc = (headers.get("Content-Encoding") or "").lower()
    if "gzip" in enc or body[:2] == b"\x1f\x8b":
        return gzip.decompress(body)
    if "deflate" in enc:
        try:
            return zlib.decompress(body)
        except zlib.error:
            return zlib.decompress(body, -zlib.MAX_WBITS)
    return body


def _get(url, data=None, timeout=20, public=False):
    req = urllib.request.Request(_iri(url), data=data, headers={
        "User-Agent": UA, "Accept-Language": "ru,en;q=0.8" if current() == "ru" else "en,ru;q=0.8"})
    err = None
    for ctx in _contexts():
        try:
            handlers = [urllib.request.HTTPSHandler(context=ctx)]
            if public:
                handlers.append(_PublicRedirects())
            opener = urllib.request.build_opener(*handlers)
            with opener.open(req, timeout=timeout) as r:
                charset = r.headers.get_content_charset() or "utf-8"
                return r.geturl(), _unpack(r.read(4_000_000), r.headers).decode(charset, "replace")
        except urllib.error.URLError as e:
            if not isinstance(e.reason, ssl.SSLCertVerificationError):
                raise
            err = e
    raise err


def _clean(text):
    return html.unescape(re.sub(r"<.*?>", "", text)).strip()


def _ddg(query, limit):
    _, body = _get("https://html.duckduckgo.com/html/",
                   urllib.parse.urlencode({"q": query, "kl": "ru-ru" if current() == "ru" else "wt-wt"}).encode())
    blocks = re.split(r'<div class="result results_links', body)[1:]
    found = []
    for b in blocks:
        a = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)
        if not a or "result--ad" in b[:200]:
            continue
        href = html.unescape(a.group(1))
        # Ссылки выдачи ведут через переадресацию DuckDuckGo: настоящий адрес — в uddg.
        q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        url = q.get("uddg", [href])[0]
        snip = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', b, re.S)
        found.append({"title": _clean(a.group(2)), "url": url,
                      "snippet": _clean(snip.group(1)) if snip else ""})
        if len(found) >= limit:
            break
    return found


def _wiki(query, limit):
    found = []
    for lang in (("ru", "en") if current() == "ru" else ("en", "ru")):
        _, body = _get(f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            {"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": limit}))
        for x in json.loads(body)["query"]["search"]:
            found.append({"title": x["title"],
                          "url": f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(x["title"].replace(" ", "_")),
                          "snippet": _clean(x.get("snippet", ""))})
        if found:
            break
    return found[:limit]


def web_search(query, limit=8):
    try:
        found = _ddg(query, limit)
    except Exception:
        found = []
    source = "DuckDuckGo"
    if not found:
        found = _wiki(query, limit)
        source = t("Википедия")
    if not found:
        return t("Ничего не найдено."), []
    lines = [tf("Результаты поиска ({source}) по запросу «{q}»:", source=source, q=query)]
    for i, f in enumerate(found, 1):
        lines.append(f"{i}. {f['title']}\n   {f['url']}\n   {f['snippet']}")
    return "\n".join(lines), found


FAKE_IP = __import__("ipaddress").ip_network("198.18.0.0/15")


def _public(url):
    """Модель зовёт open_url по просьбе страницы, которую только что прочла.
    Адреса этого Mac и домашней сети ей недоступны: иначе чужая страница
    могла бы попросить прочесть роутер или локальный сервер и унести ответ
    в следующем поисковом запросе."""
    import ipaddress
    import socket

    def inside(ip):
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast

    host = (urllib.parse.urlsplit(url).hostname or "").lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".lan", ".internal", ".home.arpa")):
        return False
    try:
        return not inside(ipaddress.ip_address(host))
    except ValueError:
        pass                    # имя, а не адрес
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return True             # не разрешилось — пусть ошибку даст сам запрос
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        # 198.18.0.0/15 — подставные адреса прокси с fake-ip: настоящий адрес
        # узнаёт уже прокси, а для имени во внешнем интернете он внешний.
        if ip in FAKE_IP:
            continue
        if inside(ip):
            return False
    return True


class _PublicRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not re.match(r"https?://", newurl) or not _public(newurl):
            raise urllib.error.URLError("переадресация во внутреннюю сеть")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(url):
    import trafilatura
    if not re.match(r"https?://", url):
        url = "https://" + url
    if not _public(url):
        raise ValueError("адрес во внутренней сети")
    final, body = _get(url, timeout=25, public=True)
    text = trafilatura.extract(body, url=final, include_links=False, favor_recall=True) or ""
    if not text:
        text = _clean(re.sub(r"(?s)<(script|style).*?</\1>", "", body))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    cut = len(text) > PAGE_LIMIT
    return tf("Страница {url}:", url=final) + f"\n\n{text[:PAGE_LIMIT]}" + ("\n\n" + t("[дальше обрезано]") if cut else "")
