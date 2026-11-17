# PARTS GARAGE

Автомагазин запчастей под заказ: frontend на GitHub Pages и backend на FastAPI.

## Frontend

Сайт: https://egorfateew-ops.github.io/parts-garage/

Файлы:
- index.html — интерфейс магазина.
- styles.css — адаптивная тема.
- app.js — каталог, корзина, формы и поиск по VIN.
- config.js — публичный URL backend. Секреты API здесь не хранить.

## Backend / TecDoc

Backend находится в папке backend. Он проксирует запросы к TecAlliance и держит ключи только на сервере.

- POST /api/v1/vehicles/identify — VIN → варианты автомобиля и TecDoc KType/NType.
- GET /api/v1/vehicles/{ktype}/articles — запчасти, связанные с выбранным KType.
- GET /api/health — состояние сервиса и интеграций.

### Запуск backend

1. Скопируй backend/.env.example в backend/.env.
2. Заполни реквизиты из договора/документации TecAlliance.
3. Установи зависимости из backend/requirements.txt.
4. Запусти из папки backend: uvicorn app.main:app --reload --port 8000.

### Публикация backend на Render

В корне репозитория есть render.yaml.

1. В Render выбери New + → Blueprint.
2. Подключи репозиторий egorfateew-ops/parts-garage.
3. Render прочитает render.yaml и создаст сервис parts-garage-api.
4. Добавь секреты и параметры TecAlliance в Environment.
5. После запуска проверь /api/health и /docs.

Ожидаемый адрес backend: https://parts-garage-api.onrender.com. Если Render назначит другой адрес, обнови PG_API_BASE_URL в config.js.

## Что нужно получить от TecAlliance

Нужна активная лицензия/доступ к:
- Vehicle Identification Service (глобальный VIN endpoint);
- TecDoc Web Service для поиска деталей по KType.

Попроси у TecAlliance:
- API key / token и точный способ авторизации;
- endpoint VIN-сервиса и разрешённые страны;
- endpoint TecDoc Web Service;
- Provider ID, если он предусмотрен вашим договором; (backend exposes TECDOC_PROVIDER_ID and {provider_id} template placeholder)
- пример запроса и ответа для поиска статей по KType;
- коды product groups для категорий магазина;
- ограничения по запросам, показу фотографий и хранению каталожных данных.

Backend VIN-адаптер использует документированный путь /api/v1/vin/{country}/{vin}. Parts-адаптер настраивается по вашему лицензированному контракту: TecDoc предлагает разные варианты Web Service, и публичная документация OneDB относится к отдельному China API. Не подставляй China endpoint в глобальный магазин без подтверждения TecAlliance.

## Важные ограничения

- Без выданных TecAlliance реквизитов API не сможет вернуть реальные данные.
- Текущий parts-адаптер ожидает JSON endpoint и JSON request template. Если в лицензии выдадут SOAP/XML, понадобится соответствующий SOAP-адаптер.
- TecDoc даёт каталожные данные, применимость, артикулы и доступные изображения. Цена продажи и наличие на складе требуют отдельной интеграции с поставщиком/ERP.
- Кнопка запроса цены в текущем frontend пока сохраняет заявку локально в браузере; отправка менеджеру и серверная база заказов — отдельный следующий этап.
- Не добавляй API-ключи в GitHub, config.js или frontend. Храни их только в Render Environment/Secrets.
