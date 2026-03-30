ARG BUILD_FROM
FROM ${BUILD_FROM}

# Установка системных зависимостей
RUN apk add --no-cache \
    ffmpeg \
    opencv \
    tesseract-ocr \
    tesseract-ocr-data-rus \
    tesseract-ocr-data-eng \
    libjpeg \
    libwebp \
    libpng \
    libtiff \
    openblas \
    libgomp

# Установка Python зависимостей
RUN pip3 install --no-cache-dir \
    easyocr==1.7.1 \
    opencv-python-headless==4.9.0.80 \
    numpy==1.26.4 \
    Pillow==10.2.0 \
    aiohttp==3.9.3 \
    websockets==12.0 \
    pyyaml==6.0.1

# Копирование скриптов
COPY *.py /app/

WORKDIR /app

CMD ["python3", "main.py"]
