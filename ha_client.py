"""
Клиент для взаимодействия с Home Assistant через WebSocket API.
"""
import asyncio
import logging
from typing import Optional, Dict, Any
import websockets
import json
from datetime import datetime

_LOGGER = logging.getLogger(__name__)


class HomeAssistantClient:
    """Клиент для подключения к Home Assistant WebSocket API."""

    def __init__(self, ha_url: str, ha_token: str):
        self.ha_url = ha_url
        self.ha_token = ha_token
        self.ws_url = self._get_ws_url(ha_url)
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self._message_id = 0

    def _get_ws_url(self, url: str) -> str:
        """Преобразует HTTP URL в WebSocket URL."""
        if url.startswith("https://"):
            return url.replace("https://", "wss://") + "/api/websocket"
        else:
            return url.replace("http://", "ws://") + "/api/websocket"

    async def connect(self) -> bool:
        """Подключение к Home Assistant."""
        try:
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }
            self.websocket = await websockets.connect(self.ws_url, extra_headers=headers)
            
            # Проверка авторизации
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("type") == "auth_ok":
                self.connected = True
                _LOGGER.info("Успешное подключение к Home Assistant")
                return True
            else:
                _LOGGER.error(f"Ошибка авторизации: {data}")
                return False
                
        except Exception as e:
            _LOGGER.error(f"Ошибка подключения к Home Assistant: {e}")
            return False

    async def disconnect(self):
        """Отключение от Home Assistant."""
        if self.websocket:
            await self.websocket.close()
        self.connected = False

    async def _send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Отправка сообщения и получение ответа."""
        if not self.websocket:
            raise RuntimeError("Нет подключения к Home Assistant")
        
        self._message_id += 1
        message["id"] = self._message_id
        
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        return json.loads(response)

    async def fire_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Отправка события в Home Assistant."""
        try:
            message = {
                "type": "event",
                "event_type": event_type,
                "data": data
            }
            response = await self._send_message(message)
            
            if response.get("success"):
                _LOGGER.info(f"Событие {event_type} отправлено")
                return True
            else:
                _LOGGER.error(f"Ошибка отправки события: {response}")
                return False
                
        except Exception as e:
            _LOGGER.error(f"Ошибка при отправке события: {e}")
            return False

    async def update_sensor(self, entity_id: str, state: str, attributes: Dict[str, Any]) -> bool:
        """Обновление состояния сенсора."""
        try:
            # Используем REST API для обновления состояния
            import aiohttp
            
            rest_url = self.ha_url.rstrip("/") + f"/api/states/{entity_id}"
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "state": state,
                "attributes": attributes
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(rest_url, json=data, headers=headers) as response:
                    if response.status == 200:
                        _LOGGER.info(f"Сенсор {entity_id} обновлён")
                        return True
                    else:
                        _LOGGER.error(f"Ошибка обновления сенсора: {response.status}")
                        return False
                        
        except Exception as e:
            _LOGGER.error(f"Ошибка при обновлении сенсора: {e}")
            return False

    async def register_service(self, domain: str, service: str, handler) -> bool:
        """Регистрация сервиса в Home Assistant."""
        try:
            message = {
                "type": "register_service",
                "domain": domain,
                "service": service,
                "target": {},
                "fields": {}
            }
            # Отправляем регистрацию
            response = await self._send_message(message)
            _LOGGER.info(f"Сервис {domain}.{service} зарегистрирован: {response}")
            return True
            
        except Exception as e:
            _LOGGER.error(f"Ошибка регистрации сервиса: {e}")
            return False

    async def call_service(self, domain: str, service: str, data: Dict[str, Any] = None) -> bool:
        """Вызов сервиса Home Assistant."""
        try:
            message = {
                "type": "call_service",
                "domain": domain,
                "service": service,
                "service_data": data or {}
            }
            response = await self._send_message(message)
            
            if response.get("success"):
                _LOGGER.info(f"Сервис {domain}.{service} вызван")
                return True
            else:
                _LOGGER.error(f"Ошибка вызова сервиса: {response}")
                return False
                
        except Exception as e:
            _LOGGER.error(f"Ошибка при вызове сервиса: {e}")
            return False
