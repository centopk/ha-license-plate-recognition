# License Plate Recognition Add-on для Home Assistant

Аддон для распознавания автомобильных номеров с камер Reolink через RTSP поток. Использует EasyOCR для распознавания текста локально на устройстве Home Assistant OS.

## Возможности

- 📷 Подключение к камере Reolink через RTSP поток
- 🔍 Распознавание российских автомобильных номеров (формат: у146тр69)
- 🏠 Интеграция с Home Assistant через WebSocket API
- 💾 Сохранение снимков в `/media/license_plates/`
- ⚙️ Настройка порога уверенности и фильтрация по региону
- 🌐 Webhook API для ручного запуска распознавания

## Требования

- Home Assistant OS
- Камера Reolink с поддержкой RTSP
- Минимум 1 ГБ свободной памяти (для работы EasyOCR)
- Процессор с поддержкой SSE4 (для OpenCV)

## Установка через GitHub (рекомендуется)


### Шаг 1: Добавьте репозиторий в Home Assistant

1. В Home Assistant перейдите в **Supervisor** → **Add-on Store**

2. Нажмите **⋮** (три точки в правом верхнем углу) → **Repositories**

3. Вставьте URL вашего репозитория:
   ```
   https://github.com/centopk/ha-license-plate-recognition
   ```

4. Нажмите **Add**

### Шаг 2: Установите аддон

1. В Add-on Store появится новый аддон "License Plate Recognition"

2. Нажмите на него → **Install**

3. После установки перейдите на вкладку **Configuration** и настройте параметры

4. Нажмите **Start** для запуска

### Альтернатива: Локальная установка

1. Подключитесь к Home Assistant через SSH или Samba

2. Скопируйте файлы в директорию `/addons`:
   ```bash
   mkdir -p /addons/license_plate_recognition
   cp -r * /addons/license_plate_recognition/
   ```

3. Перезагрузите Supervisor:
   ```bash
   ha supervisor reload
   ```

4. Установите аддон через UI: **Supervisor** → **Add-on Store** → (внизу страницы) → **License Plate Recognition** → **Install**

## Настройка

После установки настройте аддон через UI Home Assistant:

| Параметр | Описание | Пример |
|----------|----------|--------|
| `rtsp_url` | URL RTSP потока камеры | `rtsp://192.168.1.100:554/stream1` |
| `ha_url` | URL Home Assistant | `http://homeassistant.local:8123` |
| `ha_token` | Long-lived access token | (см. ниже) |
| `save_images` | Сохранять снимки | `true` / `false` |
| `confidence` | Порог уверенности OCR | `0.7` |
| `region` | Код региона для фильтрации | `69` |
| `camera_name` | Имя камеры | `Reolink Camera` |

### Получение Home Assistant Token

1. Перейдите в профиль пользователя: **Профиль** → **Безопасность**

2. Создайте новый **Long-Lived Access Token**

3. Скопируйте токен и вставьте в поле `ha_token`

### RTSP URL для камер Reolink

Обычно имеет формат:
```
rtsp://username:password@IP_КАМЕРЫ:554/stream1
rtsp://username:password@IP_КАМЕРЫ:554/stream2  (субпоток)
```

Пример:
```
rtsp://admin:MyPassword123@192.168.1.100:554/stream1
```

## Использование

### Запуск распознавания

#### Через Webhook (HTTP запрос)

```bash
curl -X POST http://IP_HOMEASSISTANT:8080/capture
```

#### Через автоматизацию Home Assistant

```yaml
automation:
  - alias: "Распознать номер по движению"
    trigger:
      - platform: state
        entity_id: binary_sensor.reolink_motion
        to: "on"
    action:
      - service: rest_command.trigger_license_plate_capture
```

#### Через Developer Tools

1. Перейдите в **Инструменты разработчика** → **Сервисы**

2. Выберите сервис: `rest_command.trigger_license_plate_capture`

3. Нажмите **Выполнить**

### События

Аддон отправляет событие `license_plate_detected` с данными:

```json
{
  "plate": "У146ТР69",
  "confidence": 0.85,
  "image_path": "/media/license_plates/У146ТР69_20260330_143022.jpg",
  "timestamp": "2026-03-30T14:30:22.123456",
  "camera_name": "Reolink Camera",
  "success": true
}
```

### Сенсоры

Создаётся сенсор с последним распознанным номером:
- Entity ID: `sensor.license_plate_<camera_name>`
- State: распознанный номер или `no_plate`

### Пример автоматизации

```yaml
automation:
  - alias: "Уведомление о распознанном номере"
    trigger:
      - platform: event
        event_type: license_plate_detected
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.success == true }}"
    action:
      - service: notify.telegram
        data:
          message: "Распознан номер: {{ trigger.event.data.plate }}"
          data:
            photo:
              file: "{{ trigger.event.data.image_path }}"
```

## Проверка состояния

### Health Check Endpoint

```bash
curl http://IP_HOMEASSISTANT:8080/health
```

Ответ:
```json
{
  "status": "healthy",
  "camera_connected": true,
  "ha_connected": true,
  "ocr_ready": true
}
```

## Логи

Логи аддона доступны в:
- **Supervisor** → **Add-ons** → **License Plate Recognition** → **Logs**

Или через SSH:
```bash
ha addons logs license_plate_recognition
```

## Производительность

- Время распознавания: ~2-5 секунд на кадр (CPU)
- Использование памяти: ~500-800 МБ
- Использование CPU: кратковременно до 100% во время распознавания

### Оптимизация

Для ускорения распознавания:
1. Используйте субпоток камеры (меньшее разрешение)
2. Настройте зону распознавания в кадре
3. Рассмотрите GPU ускорение (требуется модификация Dockerfile)

## Устранение неполадок

### Не удаётся подключиться к камере

1. Проверьте RTSP URL
2. Убедитесь, что камера доступна из сети Home Assistant
3. Проверьте логин/пароль в RTSP URL

### Низкое качество распознавания

1. Уменьшите `confidence` до 0.5
2. Улучшите освещение в зоне распознавания
3. Настройте угол камеры для лучшего вида номеров

### Ошибка "Не удалось получить кадр"

1. Проверьте, что камера не используется другим приложением
2. Перезапустите камеру
3. Используйте субпоток (stream2)

### Аддон не запускается

1. Проверьте логи в Supervisor
2. Убедитесь, что `ha_token` действителен
3. Проверьте доступность Home Assistant по `ha_url`

## Структура проекта

```
ha-license-plate-recognition/
├── addon/
│   ├── config.yaml          # Конфигурация аддона
│   ├── Dockerfile           # Образ Docker
│   ├── main.py              # Основной скрипт
│   ├── ha_client.py         # Home Assistant API клиент
│   ├── reolink.py           # Интеграция с камерой
│   └── ocr.py               # EasyOCR обёрка
├── requirements.txt         # Python зависимости
└── README.md                # Этот файл
```

## Лицензия

MIT License

## Поддержка

При возникновении проблем создайте issue в репозитории проекта.
