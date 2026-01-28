# Доступ к тенантам

## Обзор

Проект поддерживает 2 независимых тенанта с полной изоляцией данных. Каждый тенант имеет своих админов и работников.

## ⚠️ Важно: Маршрутизация по доменам

Каждый тенант определяется по домену запроса:
- `localhost` → Tenant 1
- `tenant1.localhost` → Tenant 1
- `tenant2.localhost` → Tenant 2

**Пользователи привязаны к тенанту, поэтому:**
- `admin_5` может логиниться только через `localhost` или `tenant1.localhost`
- `admin_6` может логиниться только через `tenant2.localhost`

---

## Tenant 1

**Домены:**
- `http://localhost:8000` (localhost)
- `http://tenant1.localhost:8000` (поддомен)

**Админ-панель:**
- URL: `http://localhost:8000/admin`
- Логин: `admin_5`
- Пароль: `admin123`

**API Авторизация:**
- Endpoint: `http://localhost:8000/api/auth/token/`
- Админ: `admin_5` / `admin123`
- Работник: `worker_5` / `worker123`

**Пользователи:**
- Админ: admin_5 (Администратор)
- Работник: worker_5 (Работник)

---

## Tenant 2

**Домены:**
- `http://tenant2.localhost:8000` (поддомен)

**Админ-панель:**
- URL: `http://tenant2.localhost:8000/admin`
- Логин: `admin_6`
- Пароль: `admin123`

**API Авторизация:**
- Endpoint: `http://tenant2.localhost:8000/api/auth/token/`
- Админ: `admin_6` / `admin123`
- Работник: `worker_6` / `worker123`

**Пользователи:**
- Админ: admin_6 (Администратор)
- Работник: worker_6 (Работник)

---

## Изоляция данных

✅ **Полная изоляция:**
- Пользователи Tenant 1 не могут логиниться в Tenant 2
- Данные каждого тенанта хранятся в отдельной схеме БД
- Админ-панель каждого тенанта видит только своих пользователей

✅ **Проверено:**
- Админ Tenant 1 (admin_5) не может логиниться в Tenant 2 (получает 401)
- Каждый тенант имеет независимые пользователи и данные

---

## Настройка hosts файла (для локального тестирования)

Добавьте в `C:\Windows\System32\drivers\etc\hosts`:

```
127.0.0.1 localhost
127.0.0.1 tenant1.localhost
127.0.0.1 tenant2.localhost
```

После этого можно обращаться к тенантам по доменам:
- `http://tenant1.localhost:8000` → Tenant 1
- `http://tenant2.localhost:8000` → Tenant 2

---

## Примеры запросов

### Логин в Tenant 1 (через localhost)

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"worker_5","password":"worker123"}'
```

### Логин в Tenant 2 (через tenant2.localhost)

```bash
curl -X POST http://tenant2.localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_6","password":"admin123"}'
```

### Попытка логина Tenant 1 в Tenant 2 (должна вернуть 401)

```bash
curl -X POST http://tenant2.localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_5","password":"admin123"}'
```

---

## Структура БД

**Public Schema (общая):**
- Таблица `customers_client` — информация о тенантах
- Таблица `customers_domain` — домены тенантов

**Tenant 1 Schema (tenant_1):**
- Таблица `users_app_user` — пользователи Tenant 1
- Таблица `tasks_task` — задачи Tenant 1
- Таблица `media_app_media` — медиа Tenant 1

**Tenant 2 Schema (tenant_2):**
- Таблица `users_app_user` — пользователи Tenant 2
- Таблица `tasks_task` — задачи Tenant 2
- Таблица `media_app_media` — медиа Tenant 2

---

## Дополнительная информация

Для подробной информации об API авторизации см. `AUTH_API.md`
