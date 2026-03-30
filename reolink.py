"""
Модуль для получения изображений с камеры Reolink через RTSP поток.
"""
import cv2
import logging
from typing import Optional, Tuple
import numpy as np

_LOGGER = logging.getLogger(__name__)


class ReolinkCamera:
    """Класс для подключения к камере Reolink и получения кадров."""

    def __init__(self, rtsp_url: str):
        self.rtsp_url = rtsp_url
        self.cap: Optional[cv2.VideoCapture] = None
        self._connected = False

    async def connect(self) -> bool:
        """Подключение к RTSP потоку камеры."""
        try:
            self.cap = cv2.VideoCapture(self.rtsp_url)
            
            if not self.cap.isOpened():
                _LOGGER.error("Не удалось открыть RTSP поток")
                return False
            
            # Проверка получения кадра
            ret, frame = self.cap.read()
            if not ret:
                _LOGGER.error("Не удалось получить кадр с камеры")
                self.cap.release()
                return False
            
            self._connected = True
            _LOGGER.info(f"Успешное подключение к камере: {self.rtsp_url}")
            return True
            
        except Exception as e:
            _LOGGER.error(f"Ошибка подключения к камере: {e}")
            return False

    async def disconnect(self):
        """Отключение от камеры."""
        if self.cap:
            self.cap.release()
        self._connected = False

    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Получение текущего кадра из RTSP потока.
        
        Returns:
            Кадр в формате BGR (OpenCV) или None при ошибке
        """
        if not self.cap or not self._connected:
            _LOGGER.error("Нет подключения к камере")
            return None
        
        ret, frame = self.cap.read()
        if not ret:
            _LOGGER.warning("Не удалось получить кадр, попытка переподключения...")
            self.cap.release()
            self.cap = cv2.VideoCapture(self.rtsp_url)
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    return frame
            
            return None
        
        return frame

    def capture_frame_jpeg(self) -> Optional[bytes]:
        """
        Получение кадра в формате JPEG.
        
        Returns:
            JPEG изображение в байтах или None при ошибке
        """
        frame = self.capture_frame()
        if frame is None:
            return None
        
        # Кодируем в JPEG
        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            _LOGGER.error("Ошибка кодирования кадра в JPEG")
            return None
        
        return buffer.tobytes()

    def save_frame(self, filepath: str) -> bool:
        """
        Сохранение кадра в файл.
        
        Args:
            filepath: Путь для сохранения файла
            
        Returns:
            True при успешном сохранении
        """
        frame = self.capture_frame()
        if frame is None:
            return False
        
        try:
            cv2.imwrite(filepath, frame)
            _LOGGER.info(f"Кадр сохранён: {filepath}")
            return True
        except Exception as e:
            _LOGGER.error(f"Ошибка сохранения кадра: {e}")
            return False

    def get_frame_size(self) -> Tuple[int, int]:
        """Получение размера кадра (ширина, высота)."""
        if not self.cap:
            return (0, 0)
        
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (width, height)

    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Предобработка изображения для улучшения распознавания OCR.
        
        Args:
            frame: Исходный кадр
            
        Returns:
            Обработанный кадр
        """
        # Конвертация в grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Повышение резкости
        kernel = np.array([[0, -1, 0],
                          [-1, 5, -1],
                          [0, -1, 0]])
        sharpened = cv2.filter2D(gray, -1, kernel)
        
        # Увеличение контраста через CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(sharpened)
        
        # Удаление шума
        denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
        
        return denoised
