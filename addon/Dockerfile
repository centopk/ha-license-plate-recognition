ARG BUILD_FROM
FROM ${BUILD_FROM}

# Установка системных зависимостей
RUN apk add --no-cache \
    ffmpeg \
    tesseract-ocr \
    tesseract-ocr-data-rus \
    tesseract-ocr-data-eng \
    libjpeg-turbo \
    libwebp \
    libpng \
    tiff \
    libgomp \
    py3-pip

# Установка Python зависимостей
RUN pip3 install --no-cache-dir --break-system-packages \
    torch --index-url https://download.pytorch.org/whl/cpu \
    easyocr \
    opencv-python-headless \
    numpy \
    Pillow \
    aiohttp \
    websockets \
    pyyaml

# Копирование скриптов
COPY *.py /app/

WORKDIR /app

CMD ["python3", "main.py"]
