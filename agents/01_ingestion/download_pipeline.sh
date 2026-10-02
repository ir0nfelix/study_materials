#!/bin/bash

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 \"<query>\" <limit>"
    exit 1
fi

# Отключаем прокси для yt-dlp, так как под VPN он блокируется
unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY

QUERY="$1"
LIMIT="$2"
RAW_DIR="../../raw_transcripts"
CACHE_DIR=${APP_CACHE_DIR:-../../.cache}
COOKIES_FILE="$CACHE_DIR/cookies.txt"
TMP_FILE=$(mktemp)
BROWSER="chrome"

mkdir -p "$CACHE_DIR"
rm -f "$COOKIES_FILE"

echo "======================================"
echo "🍪 Экспортируем куки из браузера в $COOKIES_FILE..."
echo "======================================"
# Первая команда: просто дергаем любое видео без скачивания, чтобы yt-dlp вытащил куки из браузера в файл
./venv/bin/yt-dlp "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
    --cookies-from-browser "$BROWSER" \
    --cookies "$COOKIES_FILE" \
    --impersonate chrome \
    --remote-components ejs:github \
    --skip-download > /dev/null 2>&1

echo "======================================"
echo "🔍 Ищем видео по запросу: '$QUERY' (лимит: $LIMIT)"
echo "======================================"

# Создаем папку для сырых транскрипций, если её нет
mkdir -p "$RAW_DIR"

# Ищем видео и сохраняем их ID в файл
# Фильтры: не старше 1 года, длительность больше 20 минут (1200 секунд)
./venv/bin/yt-dlp "ytsearch${LIMIT}:${QUERY}" \
    --cookies "$COOKIES_FILE" \
    --impersonate chrome \
    --remote-components ejs:github \
    --dateafter today-1year \
    --match-filter "duration > 20" \
    --print id > "$TMP_FILE"

echo "✅ Найдено видео: $(wc -l < "$TMP_FILE")"
echo "======================================"
echo "📥 Скачиваем субтитры в папку $RAW_DIR..."
echo "======================================"

# Скачиваем субтитры (и автоматические, и созданные вручную) для всех ID из файла
# Формат имени файла: Название видео [ID].ru.vtt
cat "$TMP_FILE" | xargs -n 1 -P 5 -I {} ./venv/bin/yt-dlp "{}" \
    --cookies "$COOKIES_FILE" \
    --impersonate chrome \
    --remote-components ejs:github \
    --write-sub --write-auto-sub \
    --sub-lang ru,en \
    --skip-download \
    --sub-format vtt \
    -o "${RAW_DIR}/%(title)s [%(id)s].%(ext)s"

rm -f "$TMP_FILE"

echo "======================================"
echo "🎉 Готово! Все сырые субтитры лежат в папке $RAW_DIR"
echo "Теперь AI сможет их прочитать и распарсить."
