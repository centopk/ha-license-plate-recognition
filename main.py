"""
Основной скрипт аддона для распознавания автомобильных номеров.
Интеграция с Home Assistant и камерой Reolink.
"""
import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, '/app')

from ha_client import HomeAssistantClient
from reolink import ReolinkCamera
from ocr import LicensePlateRecognizer

# Конфигурация
CONFIG_FILE = '/data/options.json'
MEDIA_PATH = '/media/license_plates'

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)


class LicensePlateAddon:
    """Основной класс аддона распознавания номеров."""

    def __init__(self):
        self.config = self._load_config()
        self.ha_client: Optional[HomeAssistantClient] = None
        self.camera: Optional[ReolinkCamera] = None
        self.ocr: Optional[LicensePlateRecognizer] = None
        self._running = False

    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации из файла options.json."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            _LOGGER.info(f"Конфигурация загружена: {config}")
            return config
            
        except Exception as e:
            _LOGGER.error(f"Ошибка загрузки конфигурации: {e}")
            # Конфигурация по умолчанию
            return {
                'rtsp_url': 'rtsp://192.168.1.100:554/stream1',
                'ha_url': 'http://homeassistant.local:8123',
                'ha_token': '',
                'save_images': True,
                'confidence': 0.7,
                'region': '69',
                'camera_name': 'Reolink Camera'
            }

    async def initialize(self) -> bool:
        """Инициализация всех компонентов."""
        _LOGGER.info("Инициализация аддона...")
        
        # Инициализация Home Assistant клиента
        self.ha_client = HomeAssistantClient(
            ha_url=self.config['ha_url'],
            ha_token=self.config['ha_token']
        )
        
        if not await self.ha_client.connect():
            _LOGGER.error("Не удалось подключиться к Home Assistant")
            return False
        
        # Инициализация камеры
        self.camera = ReolinkCamera(self.config['rtsp_url'])
        if not await self.camera.connect():
            _LOGGER.error("Не удалось подключиться к камере")
            await self.ha_client.disconnect()
            return False
        
        # Инициализация OCR
        self.ocr = LicensePlateRecognizer(
            confidence_threshold=self.config.get('confidence', 0.7),
            region=self.config.get('region')
        )
        
        # Создание директории для сохранения изображений
        if self.config.get('save_images', True):
            Path(MEDIA_PATH).mkdir(parents=True, exist_ok=True)
        
        _LOGGER.info("Инициализация завершена успешно")
        return True

    async def capture_and_recognize(self) -> Dict[str, Any]:
        """
        Получение кадра с камеры и распознавание номера.
        
        Returns:
            Результат распознавания
        """
        result = {
            'success': False,
            'plate': None,
            'confidence': 0,
            'image_path': None,
            'timestamp': datetime.now().isoformat(),
            'camera_name': self.config.get('camera_name', 'Unknown')
        }
        
        try:
            # Получение кадра
            _LOGGER.info("Получение кадра с камеры...")
            frame = self.camera.capture_frame()
            
            if frame is None:
                _LOGGER.error("Не удалось получить кадр с камеры")
                return result
            
            # Предобработка кадра
            processed_frame = self.camera.preprocess_frame(frame)
            
            # Распознавание номера
            _LOGGER.info("Распознавание номера...")
            plates = self.ocr.process_frame(processed_frame)
            
            if plates:
                # Берём первый найденный номер с максимальной уверенностью
                best_plate = max(plates, key=lambda x: x['confidence'])
                
                result['success'] = True
                result['plate'] = best_plate['full_number']
                result['confidence'] = best_plate['confidence']
                result['plate_data'] = best_plate
                
                _LOGGER.info(f"Распознан номер: {result['plate']} (уверенность: {result['confidence']:.2f})")
                
                # Сохранение изображения
                if self.config.get('save_images', True):
                    image_path = self._save_image(frame, best_plate['full_number'])
                    result['image_path'] = image_path
            else:
                _LOGGER.info("Номера не найдены")
                
                # Всё равно сохраняем изображение для отладки
                if self.config.get('save_images', True):
                    image_path = self._save_image(frame, 'no_plate')
                    result['image_path'] = image_path
            
            return result
            
        except Exception as e:
            _LOGGER.error(f"Ошибка при распознавании: {e}", exc_info=True)
            return result

    def _save_image(self, frame, plate_name: str) -> str:
        """
        Сохранение изображения в медиа директорию.
        
        Args:
            frame: Кадр изображения
            plate_name: Имя для файла (номер или 'no_plate')
            
        Returns:
            Путь к сохранённому файлу
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{plate_name}_{timestamp}.jpg"
            filepath = os.path.join(MEDIA_PATH, filename)
            
            import cv2
            cv2.imwrite(filepath, frame)
            
            _LOGGER.info(f"Изображение сохранено: {filepath}")
            
            # Возвращаем путь относительно media
            return f"/media/license_plates/{filename}"
            
        except Exception as e:
            _LOGGER.error(f"Ошибка сохранения изображения: {e}")
            return None

    async def send_result_to_ha(self, result: Dict[str, Any]):
        """
        Отправка результата в Home Assistant.
        
        Args:
            result: Результат распознавания
        """
        if not self.ha_client:
            return
        
        # Отправка события
        event_data = {
            'plate': result.get('plate'),
            'confidence': result.get('confidence'),
            'image_path': result.get('image_path'),
            'timestamp': result.get('timestamp'),
            'camera_name': result.get('camera_name'),
            'success': result.get('success', False)
        }
        
        await self.ha_client.fire_event('license_plate_detected', event_data)
        
        # Обновление сенсора
        camera_name_safe = self.config.get('camera_name', 'camera').replace(' ', '_').lower()
        entity_id = f"sensor.license_plate_{camera_name_safe}"
        
        if result.get('success'):
            await self.ha_client.update_sensor(
                entity_id=entity_id,
                state=result.get('plate', 'unknown'),
                attributes={
                    'confidence': result.get('confidence', 0),
                    'image_path': result.get('image_path'),
                    'timestamp': result.get('timestamp'),
                    'camera_name': result.get('camera_name'),
                    'friendly_name': f"License Plate {self.config.get('camera_name', 'Camera')}"
                }
            )
        else:
            await self.ha_client.update_sensor(
                entity_id=entity_id,
                state='no_plate',
                attributes={
                    'confidence': 0,
                    'image_path': result.get('image_path'),
                    'timestamp': result.get('timestamp'),
                    'camera_name': result.get('camera_name'),
                    'friendly_name': f"License Plate {self.config.get('camera_name', 'Camera')}"
                }
            )

    async def run_webhook_server(self):
        """Запуск HTTP сервера для webhook триггеров."""
        from aiohttp import web
        
        app = web.Application()
        app.router.add_post('/capture', self._handle_capture_request)
        app.router.add_get('/health', self._handle_health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        
        _LOGGER.info("Webhook сервер запущен на порту 8080")
        
        return runner

    async def _handle_capture_request(self, request: web.Request) -> web.Response:
        """Обработка запроса на распознавание."""
        try:
            _LOGGER.info("Получен запрос на распознавание номера")
            
            result = await self.capture_and_recognize()
            await self.send_result_to_ha(result)
            
            return web.json_response({
                'success': result.get('success', False),
                'plate': result.get('plate'),
                'confidence': result.get('confidence'),
                'timestamp': result.get('timestamp')
            })
            
        except Exception as e:
            _LOGGER.error(f"Ошибка обработки запроса: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def _handle_health_check(self, request: web.Request) -> web.Response:
        """Проверка состояния аддона."""
        return web.json_response({
            'status': 'healthy' if self._running else 'starting',
            'camera_connected': self.camera is not None and self.camera._connected,
            'ha_connected': self.ha_client is not None and self.ha_client.connected,
            'ocr_ready': self.ocr is not None
        })

    async def run(self):
        """Основной цикл работы аддона."""
        _LOGGER.info("Запуск аддона распознавания номеров...")
        self._running = True
        
        # Инициализация
        if not await self.initialize():
            _LOGGER.error("Ошибка инициализации, выход")
            return
        
        # Запуск webhook сервера
        runner = await self.run_webhook_server()
        
        try:
            # Основной цикл (ожидание запросов)
            while self._running:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            _LOGGER.info("Получен сигнал остановки")
        finally:
            # Очистка
            _LOGGER.info("Остановка аддона...")
            await runner.cleanup()
            
            if self.camera:
                await self.camera.disconnect()
            
            if self.ha_client:
                await self.ha_client.disconnect()
            
            self._running = False
            _LOGGER.info("Аддон остановлен")


def main():
    """Точка входа."""
    addon = LicensePlateAddon()
    
    try:
        asyncio.run(addon.run())
    except KeyboardInterrupt:
        _LOGGER.info("Остановка по Ctrl+C")
    except Exception as e:
        _LOGGER.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
