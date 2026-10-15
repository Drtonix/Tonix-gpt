"""Язык интерфейса. Ключ перевода — сама русская строка."""
import os

from PySide6.QtCore import QLocale, QSettings

LANGS = ("ru", "en")
SETTINGS = os.environ.get("TONIX_GPT_SETTINGS", "tonix-gpt")

EN = {
    "{mb} МБ/с": "{mb} MB/s",
    "МБ/с": "MB/s",
    "ещё {h} ч {m} мин": "{h} h {m} min left",
    "ещё {m} мин": "{m} min left",
    "в очереди": "queued",
    ", перед ней {n}": ", {n} ahead",
    ", следующая": ", next",
    "не вышло: {e}": "failed: {e}",
    "Новый чат": "New chat",
    "Настройки": "Settings",
    "Сообщение": "Message",
    "Картинка": "Image",
    "Картинки": "Images",
    "Интернет": "Internet",
    "Рисование": "Drawing",
    "Размышления": "Thinking",
    "Отправить": "Send",
    "Стоп": "Stop",
    "Нет скачанных моделей": "No models downloaded",
    "Модель сама ищет и читает страницы, когда нужны свежие данные":
        "The model searches and reads pages when it needs fresh data",
    "Модель рисует, когда просят: Z-Image Turbo, около 30 с на картинку":
        "The model draws when asked: Z-Image Turbo, about 30 s per image",
    "Прежде чем ответить, модель рассуждает: точнее, но дольше":
        "The model reasons before answering: more accurate, but slower",
    "Переименовать": "Rename",
    "Название": "Title",
    "Удалить": "Delete",
    "Отмена": "Cancel",
    "Удалить чат «{title}»?": "Delete chat “{title}”?",
    "Открыть": "Open",
    "Показать в Finder": "Show in Finder",
    "Сохранить как…": "Save as…",
    "Сохранить": "Save",
    "Убрать": "Remove",
    "Не вышло: ": "Failed: ",
    " — не вышло: {e}": " — failed: {e}",
    "сервер моделей остановился — подробности в server.log": "the model server stopped — see server.log",
    "О программе {name}": "About {name}",
    "Закрыть": "Close",
    "вставка": "paste",
    "Язык": "Language",
    "Оформление": "Appearance",
    "Как в системе": "System",
    "Светлое": "Light",
    "Тёмное": "Dark",
    "Куда качать": "Download to",
    "Общая для всех приложений": "Shared by all apps",
    "Встроенный диск": "Built-in disk",
    "встроенный диск": "built-in disk",
    "внешний диск": "external drive",
    "внешний диск не подключён": "external drive not connected",
    " — не подключён": " — not connected",
    "Встроенный диск · общий кэш Hugging Face": "Built-in disk · shared Hugging Face cache",
    "Выбрать папку…": "Choose folder…",
    "Папка для моделей": "Models folder",
    "ГБ": "GB",
    "Остановить": "Stop",
    "Скачать": "Download",
    "Докачать": "Resume",
    "скачано {gb} ГБ": "{gb} GB downloaded",
    "Удалить {name}?": "Delete {name}?",
    "Освободится {gb} ГБ.": "Frees {gb} GB.",
    " Она в общем кэше — другим приложениям, которые ею пользуются, придётся скачать её заново.":
        " It is in the shared cache — other apps that use it will have to download it again.",
    "Модели": "Models",
    "Загрузка модели…": "Loading model…",
    "Ответ…": "Answering…",
    "Поиск: «{q}»": "Search: “{q}”",
    "Страница: ": "Page: ",
    "Рисунок": "Image",
    "Освобождение памяти…": "Freeing memory…",
    "Загрузка модели рисования…": "Loading the drawing model…",
    "Рисование · шаг {n} из {total}": "Drawing · step {n} of {total}",
    "остановлено": "stopped",
    "не нарисовалось": "the image failed",
    "сервер моделей не запустился — подробности в server.log": "the model server did not start — see server.log",
    "сервер моделей не отвечает": "the model server does not respond",
    "ошибка модели": "model error",
    "{name} лежит на внешнем диске, он не подключён": "{name} is on an external drive that is not connected",
    "{name} не скачана — она в «Настройках»": "{name} is not downloaded — see Settings",
    "Ты — собеседник в приложении tonix-gpt на компьютере пользователя. "
    "Отвечай на языке, на котором пишут тебе. Оформляй ответ Markdown, когда это помогает.":
        "You are a conversation partner in the tonix-gpt app on the user's computer. "
        "Reply in the language you are addressed in. Use Markdown when it helps.",
    "Сейчас {date}.": "It is {date} now.",
    "У тебя есть интернет: web_search ищет, open_url читает страницу. Ищи, когда нужны "
    "свежие данные — новости, цены, погода, расписания, — или когда не уверен в факте. "
    "Цифры и факты бери только из найденного: если в выдержках поиска нужного нет, открой "
    "страницу через open_url. Источник называй ссылкой на ту страницу, откуда взял, — "
    "не придумывай источники, которых не открывал и не видел в выдаче.":
        "You have internet access: web_search searches, open_url reads a page. Search when you need "
        "fresh data — news, prices, weather, schedules — or when you are unsure of a fact. "
        "Take numbers and facts only from what you found: if the search snippets lack them, open "
        "the page with open_url. Cite as a link the page you took it from — "
        "never invent sources you have not opened or seen in the results.",
    "Интернета у тебя сейчас нет: о свежих событиях можешь не знать — так и скажи.":
        "You have no internet right now: you may not know recent events — say so.",
    "generate_image рисует картинку по описанию: зови его, когда просят нарисовать "
    "или показать что-то картинкой. Описание пиши подробно и по-английски.":
        "generate_image draws a picture from a description: call it when asked to draw "
        "or show something as an image. Write the description in detail, in English.",
    "Что на картинке?": "What is in the picture?",
    "\n\n[приложено картинок: {n} — эта модель их не видит]":
        "\n\n[{n} image(s) attached — this model cannot see them]",
    "Этот запрос уже был — результаты выше.": "This query was already made — results are above.",
    "\n\nНайдено в интернете:\n\n": "\n\nFound on the internet:\n\n",
    "\n\nПоиск закончен. Ответь на вопрос по найденному, без новых запросов.":
        "\n\nSearch is over. Answer from what was found, without new queries.",
    "Картинка нарисована и уже показана пользователю. Коротко скажи, что получилось.":
        "The image is drawn and already shown to the user. Briefly say what came out.",
    "Инструмента {name} нет.": "There is no tool {name}.",
    "Не вышло: {e}": "Failed: {e}",
    "Поиск в интернете. Возвращает заголовки, адреса и короткие выдержки. "
    "Для свежих новостей, цен, погоды, фактов, которых модель может не знать.":
        "Web search. Returns titles, addresses and short snippets. "
        "For fresh news, prices, weather and facts the model may not know.",
    "Поисковый запрос": "Search query",
    "Открыть страницу по адресу и прочитать её текст.": "Open a page by its address and read its text.",
    "Адрес страницы": "Page address",
    "Нарисовать картинку по описанию. Описание — подробное, лучше по-английски: "
    "что изображено, стиль, свет, ракурс.":
        "Draw a picture from a description. Make it detailed, preferably in English: "
        "subject, style, lighting, angle.",
    "Описание картинки": "Picture description",
    "Формат: квадрат, вертикальная или горизонтальная": "Shape: square, portrait or landscape",
    "Википедия": "Wikipedia",
    "Ничего не найдено.": "Nothing found.",
    "Результаты поиска ({source}) по запросу «{q}»:": "Search results ({source}) for “{q}”:",
    "Страница {url}:": "Page {url}:",
    "[дальше обрезано]": "[truncated]",
}

WEEKDAYS = {"ru": ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"],
            "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
MONTHS = {"ru": ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
                 "сентября", "октября", "ноября", "декабря"],
          "en": ["January", "February", "March", "April", "May", "June", "July", "August",
                 "September", "October", "November", "December"]}

_BACK = {v: k for k, v in EN.items()}
_lang = None


def current():
    global _lang
    if _lang is None:
        saved = QSettings("local", SETTINGS).value("lang", "")
        if saved in LANGS:
            _lang = saved
        else:
            _lang = "ru" if QLocale.system().language() == QLocale.Russian else "en"
    return _lang


def set_current(lang):
    global _lang
    if lang in LANGS:
        _lang = lang
        QSettings("local", SETTINGS).setValue("lang", lang)


def key_of(text):
    if text in EN:
        return text
    return _BACK.get(text)


def t(s):
    return EN.get(s, s) if current() == "en" else s


def tf(fmt, **kw):
    return t(fmt).format(**kw)


# Подписи хода загрузки моделей — тоже на языке приложения.
import models_home  # noqa: E402

models_home.set_translator(t)
