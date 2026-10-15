#!/bin/zsh
# Самодостаточный tonix-gpt.app: свой Python, Qt, MLX. Модели в бандл не кладутся —
# они в общем кэше Hugging Face и качаются из «Настроек».
set -e
setopt null_glob
cd "${0:A:h}"
SRC="$PWD"
OUT="$SRC/build"
APP="$OUT/tonix-gpt.app"
PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/20260901/cpython-3.12.14%2B20260901-aarch64-apple-darwin-install_only_stripped.tar.gz"

say() { print -P "%F{green}==>%f $*"; }

rm -rf "$APP"
mkdir -p "$OUT" "$APP/Contents/MacOS" "$APP/Contents/Resources"
RES="$APP/Contents/Resources"

say "переносимый Python"
[ -f "$OUT/python.tar.gz" ] || curl -fsSL "$PY_URL" -o "$OUT/python.tar.gz"
mkdir -p "$RES/python"
tar xzf "$OUT/python.tar.gz" -C "$RES/python" --strip-components=1
PY="$RES/python/bin/python3"

say "библиотеки"
# Версии — ровно те, на которых всё проверено: снимок окружения разработки.
uv pip freeze -q --python .venv/bin/python > "$OUT/req.txt"
uv pip install -q --python "$PY" --break-system-packages -r "$OUT/req.txt"

say "чистка лишнего"
SP="$RES/python/lib/python3.12/site-packages"
for m in Qt3D QtCharts QtDataVis QtDesigner QtQuick3D QtSensors QtSerial QtSql \
         QtTest QtBluetooth QtNfc QtRemoteObjects QtScxml QtSpatialAudio \
         QtStateMachine QtTextToSpeech QtHelp QtUiTools QtPdf QtMultimedia \
         QtWebEngine QtWebView QtWebChannel QtWebSockets QtPositioning \
         QtLocation QtQuick QtQml QtGraphs QtVirtualKeyboard QtHttpServer; do
    rm -rf "$SP/PySide6/Qt/lib/${m}"*.framework "$SP/PySide6/${m}"* 2>/dev/null || true
done
rm -rf "$SP/PySide6/Qt/translations" "$SP/PySide6/Qt/qml" \
       "$SP/PySide6/Designer.app" "$SP/PySide6/assistant.app" \
       "$SP/PySide6/linguist.app" "$SP/PySide6/examples" 2>/dev/null || true
rm -rf "$SP/torch/include" "$SP/torch/share"
find "$RES/python/lib" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$RES/python/lib" -name "test" -type d -prune -exec rm -rf {} + 2>/dev/null || true

say "исходники"
mkdir -p "$RES/app"
cp app.py engine.py catalog.py store.py tools.py imagegen.py models_home.py _style.py i18n.py support.py "$RES/app/"
cp -R certs "$RES/app/"

say "байт-код"
# Заранее: бандл подписан и после установки не меняется (см. «подпись»).
"$PY" -m compileall -q -j 0 --invalidation-mode unchecked-hash "$RES/python/lib/python3.12" >/dev/null 2>&1 || true
"$PY" -m compileall -q --invalidation-mode unchecked-hash "$RES/app" >/dev/null

say "лицензии"
LIC="$RES/Лицензии"
mkdir -p "$LIC"
find "$SP" -maxdepth 1 -type d -name "*.dist-info" | while read -r d; do
    pkg=$(basename "$d" .dist-info)
    find "$d" -maxdepth 2 \( -name "LICENSE*" -o -name "COPYING*" -o -name "NOTICE*" \) \
        -type f 2>/dev/null | while read -r f; do
        mkdir -p "$LIC/$pkg"
        cp "$f" "$LIC/$pkg/" 2>/dev/null || true
    done
done
cat > "$LIC/О лицензиях.txt" <<'LICNOTE'
Из чего собран tonix-gpt и на каких условиях.

Qt / PySide6 — LGPL 3.0
    Библиотеки Qt лежат в приложении отдельными файлами и не вкомпилированы
    в него, поэтому их можно заменить своими сборками. Исходники:
    https://download.qt.io/official_releases/qt/

Python — PSF License

Модели в приложение не входят: каждая скачивается со своей страницы
Hugging Face и идёт под своей лицензией (Qwen — Apache 2.0, Gemma — Gemma
Terms of Use, gpt-oss — Apache 2.0, Z-Image — Apache 2.0).
LICNOTE

say "интерпретатор в MacOS"
# macOS зовёт программу по имени файла процесса: питон из Resources даёт
# в доке ракету и имя «python3». Он статический, установку находит по PYTHONHOME.
cp "$RES/python/bin/python3.12" "$APP/Contents/MacOS/tonix-gpt"

say "оболочка"
cat > "$APP/Contents/MacOS/launcher" <<'LAUNCH'
#!/bin/zsh
LOG="$HOME/Library/Logs/tonix-gpt.log"
mkdir -p "$HOME/Library/Logs"
if [ -f "$LOG" ] && [ "$(stat -f%z "$LOG")" -gt 5000000 ]; then : > "$LOG"; fi
exec >> "$LOG" 2>&1
echo "=== запуск $(date) ==="
DIR="${0:A:h}"
RES="$DIR/../Resources"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"
export PYTHONHOME="$RES/python"
# Бандл подписан и после установки не меняется: запись внутрь — и macOS
# при следующем запуске проверяет его заново. Байт-код собран заранее.
export PYTHONDONTWRITEBYTECODE=1
export NUMBA_CACHE_DIR="$HOME/Library/Caches/tonix-gpt/numba"
export HF_HUB_DISABLE_XET=1
cd "$RES/app"
exec "$DIR/tonix-gpt" "$RES/app/app.py"
LAUNCH
chmod +x "$APP/Contents/MacOS/launcher"
cp icon/AppIcon.icns "$RES/AppIcon.icns"
cp icon/Assets.car "$RES/Assets.car"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleDevelopmentRegion</key><string>ru</string>
<key>CFBundleLocalizations</key><array><string>ru</string><string>en</string></array>
<key>CFBundleDisplayName</key><string>tonix-gpt</string>
<key>CFBundleExecutable</key><string>launcher</string>
<key>CFBundleIconFile</key><string>AppIcon</string>
<key>CFBundleIconName</key><string>AppIcon</string>
<key>CFBundleIdentifier</key><string>space.bdub.tonix-gpt</string>
<key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
<key>CFBundleName</key><string>tonix-gpt</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>CFBundleVersion</key><string>1</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
<key>NSHighResolutionCapable</key><true/>
<key>NSDocumentsFolderUsageDescription</key><string>tonix-gpt прикладывает к сообщениям картинки из папки «Документы».</string>
<key>NSDownloadsFolderUsageDescription</key><string>tonix-gpt прикладывает к сообщениям картинки из папки «Загрузки».</string>
<key>NSDesktopFolderUsageDescription</key><string>tonix-gpt прикладывает к сообщениям картинки с рабочего стола.</string>
<key>NSRemovableVolumesUsageDescription</key><string>tonix-gpt прикладывает к сообщениям картинки с внешних дисков.</string>
<key>NSHumanReadableCopyright</key><string>DrTonix · bdub.space</string>
</dict></plist>
PLIST

say "подпись"
# Без подписи первый запуск большого бандла после установки — около 29 с.
codesign --force --deep --sign - "$APP" 2>/dev/null
codesign --verify --deep --strict "$APP"

say "готово: $(du -sh "$APP" | cut -f1)  ->  $APP"

# Копия в build — не второе приложение в Launchpad и Spotlight: снимаем с учёта.
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -u "$APP" >/dev/null 2>&1 || true
