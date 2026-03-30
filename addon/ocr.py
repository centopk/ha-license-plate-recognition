"""
Модуль для распознавания автомобильных номеров с помощью EasyOCR.
Специализирован для российских автомобильных номеров.
"""
import easyocr
import logging
import re
from typing import List, Tuple, Optional, Dict, Any
import numpy as np

_LOGGER = logging.getLogger(__name__)


# Паттерн российского автомобильного номера
# Формат: 1 буква, 3 цифры, 2 буквы, 2-3 цифры региона
# Пример: у146тр69, а123бв777
RUSSIAN_PLATE_PATTERN = re.compile(
    r'([АВЕКМНОРСТУХ])'      # Первая буква
    r'(\d{3})'                # 3 цифры
    r'([АВЕКМНОРСТУХ]{2})'    # 2 буквы
    r'(\d{2,3})',             # Регион (2-3 цифры)
    re.IGNORECASE
)

# Допустимые буквы в российских номерах
VALID_LETTERS = 'АВЕКМНОРСТУХ'


class LicensePlateRecognizer:
    """Класс для распознавания автомобильных номеров через EasyOCR."""

    def __init__(self, confidence_threshold: float = 0.7, region: Optional[str] = None):
        """
        Инициализация распознавателя.
        
        Args:
            confidence_threshold: Порог уверенности распознавания (0.5-0.9)
            region: Код региона для фильтрации (например, "69")
        """
        self.confidence_threshold = confidence_threshold
        self.region_filter = region
        
        # Инициализация EasyOCR с русским и английским языками
        # Английский нужен для цифр и некоторых символов
        _LOGGER.info("Инициализация EasyOCR (ru + en)...")
        self.reader = easyocr.Reader(
            ['ru', 'en'],
            gpu=False,  # CPU режим
            verbose=False
        )
        _LOGGER.info("EasyOCR готов к работе")

    def recognize(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Распознавание текста на изображении.
        
        Args:
            image: Изображение в формате BGR (OpenCV)
            
        Returns:
            Список найденных текстов с координатами и уверенностью
        """
        try:
            # Конвертация BGR в RGB для EasyOCR
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Распознавание текста
            results = self.reader.readtext(
                rgb_image,
                min_size=30,
                contrast_ths=0.3,
                adjust_contrast=0.5,
                text_threshold=0.7,
                low_text=0.4,
                link_threshold=0.4,
                canvas_size=2560,
                mag_ratio=1.0
            )
            
            formatted_results = []
            for bbox, text, confidence in results:
                formatted_results.append({
                    'text': text.strip(),
                    'confidence': confidence,
                    'bbox': bbox
                })
            
            return formatted_results
            
        except Exception as e:
            _LOGGER.error(f"Ошибка распознавания: {e}")
            return []

    def find_license_plates(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Поиск автомобильных номеров в результатах распознавания.
        
        Args:
            results: Результаты распознавания текста
            
        Returns:
            Список найденных номеров
        """
        plates = []
        
        for result in results:
            text = result['text'].upper()
            confidence = result['confidence']
            
            # Проверка порога уверенности
            if confidence < self.confidence_threshold:
                continue
            
            # Поиск паттерна номера в тексте
            match = RUSSIAN_PLATE_PATTERN.search(text)
            
            if match:
                plate_data = {
                    'full_number': match.group(0).upper(),
                    'letter1': match.group(1).upper(),
                    'digits': match.group(2),
                    'letters2': match.group(3).upper(),
                    'region': match.group(4),
                    'confidence': confidence,
                    'bbox': result.get('bbox'),
                    'raw_text': text
                }
                
                # Фильтрация по региону если указан
                if self.region_filter and plate_data['region'] != self.region_filter:
                    _LOGGER.debug(f"Номер отфильтрован по региону: {plate_data['full_number']}")
                    continue
                
                # Проверка валидности букв
                if self._validate_letters(plate_data):
                    plates.append(plate_data)
                    _LOGGER.info(f"Найден номер: {plate_data['full_number']} (уверенность: {confidence:.2f})")
        
        return plates

    def _validate_letters(self, plate: Dict[str, Any]) -> bool:
        """
        Проверка валидности букв в номере.
        
        Args:
            plate: Данные номера
            
        Returns:
            True если буквы валидны
        """
        letter1 = plate.get('letter1', '')
        letters2 = plate.get('letters2', '')
        
        # Все буквы должны быть из допустимого набора
        for letter in letter1 + letters2:
            if letter not in VALID_LETTERS:
                _LOGGER.debug(f"Недопустимая буква в номере: {letter}")
                return False
        
        return True

    def process_frame(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Полная обработка кадра: распознавание + поиск номеров.
        
        Args:
            frame: Кадр в формате BGR
            
        Returns:
            Список найденных номеров
        """
        # Распознавание текста
        results = self.recognize(frame)
        
        # Поиск номеров
        plates = self.find_license_plates(results)
        
        return plates


# Для совместимости импортируем cv2 здесь
import cv2
