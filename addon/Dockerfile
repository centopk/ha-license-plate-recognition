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
    py3-pip \
    cmake \
    make \
    g++ \
    nasm

# Установка Python зависимостей
RUN pip3 install --no-cache-dir --break-system-packages \
    torch --extra-index-url https://download.pytorch.org/whl/cpu \
    easyocr \
    numpy \
    Pillow \
    aiohttp \
    websockets \
    pyyaml \
    opencv-python-headless==4.11.0.86

# Копирование скриптов
COPY *.py /app/

WORKDIR /app

CMD ["python3", "main.py"]
