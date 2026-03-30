"""Тестовый скрипт для проверки OCR."""
import cv2
import numpy as np
import easyocr

print("Инициализация EasyOCR...")
reader = easyocr.Reader(['ru', 'en'], gpu=False)

print("Готово! EasyOCR работает.")

# Тест на простом изображении (если есть)
test_image = np.zeros((100, 300, 3), dtype=np.uint8)
test_image[:] = 255  # Белый фон

# Рисуем текст
cv2.putText(test_image, 'A123BC777', (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)

print("Выполнение распознавания...")
results = reader.readtext(test_image)

if results:
    for (bbox, text, confidence) in results:
        print(f"Распознано: {text} (уверенность: {confidence:.2f})")
else:
    print("Ничего не распознано")

print("Тест завершён успешно!")
