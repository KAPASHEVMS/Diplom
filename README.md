# ПИС расчёта конечной рыночной цены товаров

Программная реализация системы из ВКР Капашева М.С.
Стек: **Python 3.12 + PostgreSQL 15 + SQLAlchemy 2 + Alembic + Tkinter + Docker Compose**.

## Архитектура запуска

```
┌──────────────────┐        ┌─────────────────────────────────┐
│  Tkinter GUI     │  TCP   │   docker compose                │
│  (хост, локально)│ ─────▶ │                                 │
└──────────────────┘  5432  │  ┌─────────┐  ┌──────────────┐  │
                            │  │ db      │  │ worker       │  │
                            │  │ Postgres│◀─│ парсер цен   │  │
                            │  └────┬────┘  └──────────────┘  │
                            │       │       ┌──────────────┐  │
                            │       └──────▶│ migrate+seed │  │
                            │               └──────────────┘  │
                            └─────────────────────────────────┘
```

GUI запускается локально (Tkinter в Docker требует X-сервера на хосте, что
неудобно); БД и фоновый парсер — в контейнерах.

## Быстрый старт

```bash
cd program/
cp .env.example .env

# 1) Поднять БД + миграции Alembic + seed-данные + парсер-воркер
docker compose up -d --build

# 2) Запустить GUI на хосте (на Windows: scripts\run_gui.bat)
./scripts/run_gui.sh
```

Логин по умолчанию: **manager / manager123** (или **admin / admin123**).

## Структура проекта

```
program/
├── docker-compose.yml      # db + migrate + seed + worker
├── Dockerfile              # образ Python для migrate/seed/worker
├── alembic.ini             # конфиг миграций
├── alembic/
│   ├── env.py
│   └── versions/001_init.py
├── app/
│   ├── __main__.py         # entry: запуск GUI
│   ├── config.py
│   ├── db.py
│   ├── models.py           # 11 ORM-моделей по даталогической модели
│   ├── auth.py             # bcrypt-аутентификация
│   ├── seed.py             # начальные данные
│   ├── pricing/
│   │   ├── cost.py         # алгоритм 2.4.1 — себестоимость
│   │   ├── band.py         # алгоритм 2.4.2 — вилка цен (3 модели)
│   │   └── approval.py     # алгоритм 2.4.3 — утверждение
│   ├── parsers/
│   │   ├── base.py         # реестр парсеров
│   │   ├── wildberries.py  # WB через search.wb.ru API
│   │   ├── ozon.py         # Ozon best-effort
│   │   ├── demo.py         # синтетический генератор
│   │   └── runner.py       # парсер-воркер (фоновый цикл)
│   └── gui/
│       ├── app.py          # главное окно + логин
│       ├── catalog.py      # каталог товаров
│       ├── price_form.py   # форма расчёта цены
│       ├── report.py       # отчёт по утверждённым ценам
│       └── settings_frame.py
└── scripts/
    ├── run_gui.bat
    └── run_gui.sh
```

## Управление БД и миграциями

| Команда | Назначение |
|---------|-----------|
| `docker compose up -d db`                  | поднять только PostgreSQL |
| `docker compose run --rm migrate`          | применить миграции |
| `docker compose run --rm seed`             | загрузить тестовые данные |
| `docker compose up -d worker`              | запустить парсер-воркер |
| `docker compose logs -f worker`            | смотреть логи парсинга |
| `docker compose down -v`                   | снести БД и тома |

Создать новую миграцию (в активной venv c доступом к БД):
```bash
alembic revision --autogenerate -m "your_change"
alembic upgrade head
```

## Парсеры цен конкурентов

Три источника, выбираются переменной окружения `PARSER_MODE`:

| Режим | Что использует |
|-------|----------------|
| `demo` (по умолч.) | синтетические цены, детерминированные по `search_query` |
| `real`             | Wildberries (search.wb.ru) + Ozon (composer-api) |
| `wildberries`/`ozon`/`demo` | конкретный парсер |

Wildberries-парсер использует публичный JSON API без авторизации.
Ozon-парсер — best-effort (Ozon активно блокирует автоматический сбор), при
ошибке возвращает пустой список — это нормально, расчёт сделает деградацию
к рыночным данным от других источников.

Расписание: воркер запускается в цикле с интервалом `PARSER_INTERVAL_SEC`
(по умолчанию 600 с). Также можно вызвать вручную с вкладки **Настройки**
в GUI.

## Математическая модель

См. ниже в ответе ассистента и в коде модулей `app/pricing/`.
