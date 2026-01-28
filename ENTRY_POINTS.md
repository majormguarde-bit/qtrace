# Точки входа для тенантов

## Обзор

Проект поддерживает несколько точек входа для разных типов пользователей и приложений.

---

## 1. Админ-панель Django (Public Schema)

**Назначение:** Управление системой, клиентами, доменами

**URL:** `http://localhost:8000/admin`

**Аутентификация:** Django Session

**Учетные данные:**
- Username: `admin`
- Password: `admin123`

**Доступные функции:**
- Управление клиентами (Tenant 1, Tenant 2)
- Управление доменами
- Просмотр логов

---

## 2. Админ-панель Tenant 1

**Назначение:** Управление пользователями и данными Tenant 1

**URL:** `http://localhost:8000/admin` или `http://tenant1.localhost:8000/admin`

**Аутентификация:** Django Session

**Учетные данные:**
- Username: `admin_5`
- Password: `admin123`

**Доступные функции:**
- Управление пользователями Tenant 1
- Управление профилями пользователей
- Просмотр логов Tenant 1

---

## 3. Админ-панель Tenant 2

**Назначение:** Управление пользователями и данными Tenant 2

**URL:** `http://tenant2.localhost:8000/admin`

**Аутентификация:** Django Session

**Учетные данные:**
- Username: `admin_6`
- Password: `admin123`

**Доступные функции:**
- Управление пользователями Tenant 2
- Управление профилями пользователей
- Просмотр логов Tenant 2

---

## 4. API Авторизация (JWT Token)

### Endpoint: POST `/api/auth/token/`

**Назначение:** Получить JWT токен для мобильных приложений

**Домены:**
- Tenant 1: `http://localhost:8000/api/auth/token/` или `http://tenant1.localhost:8000/api/auth/token/`
- Tenant 2: `http://tenant2.localhost:8000/api/auth/token/`

**Request:**
```json
{
  "username": "worker_5",
  "password": "worker123"
}
```

**Response (200):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 2,
    "username": "worker_5",
    "email": "worker@tenant1.local",
    "first_name": "Worker",
    "last_name": "Tenant5",
    "role": "WORKER"
  }
}
```

**Примеры:**

**Tenant 1 - Админ:**
```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_5","password":"admin123"}'
```

**Tenant 1 - Работник:**
```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"worker_5","password":"worker123"}'
```

**Tenant 2 - Админ:**
```bash
curl -X POST http://tenant2.localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_6","password":"admin123"}'
```

**Tenant 2 - Работник:**
```bash
curl -X POST http://tenant2.localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"worker_6","password":"worker123"}'
```

---

## 5. API Профиль пользователя

### Endpoint: GET `/api/users/me/`

**Назначение:** Получить данные текущего авторизованного пользователя

**Аутентификация:** JWT Token (Bearer)

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "id": 2,
  "username": "worker_5",
  "email": "worker@tenant1.local",
  "first_name": "Worker",
  "last_name": "Tenant5",
  "role": "WORKER"
}
```

**Пример:**
```bash
curl -X GET http://localhost:8000/api/users/me/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## 6. API Регистрация пользователя

### Endpoint: POST `/api/users/register/`

**Назначение:** Создать нового пользователя в tenant

**Аутентификация:** Нет (публичный endpoint)

**Request:**
```json
{
  "username": "new_worker",
  "email": "worker@example.com",
  "password": "secure_password",
  "first_name": "John",
  "last_name": "Doe",
  "role": "WORKER"
}
```

**Response (201):**
```json
{
  "id": 3,
  "username": "new_worker",
  "email": "worker@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "WORKER"
}
```

---

## Маршрутизация по доменам

| Домен | Tenant | Schema |
|-------|--------|--------|
| `localhost:8000` | Tenant 1 | `tenant_1` |
| `tenant1.localhost:8000` | Tenant 1 | `tenant_1` |
| `tenant2.localhost:8000` | Tenant 2 | `tenant_2` |

---

## Типы пользователей

### ADMIN (Администратор)
- Может входить в админ-панель
- Может управлять пользователями
- Может просматривать логи
- Может использовать API

**Примеры:** admin_5, admin_6

### WORKER (Работник)
- Не может входить в админ-панель
- Может использовать API
- Может просматривать свои данные

**Примеры:** worker_5, worker_6

---

## Изоляция данных

✅ **Полная изоляция:**
- Каждый tenant имеет отдельную схему БД
- Пользователи Tenant 1 не видят данные Tenant 2
- Пользователи Tenant 2 не видят данные Tenant 1
- Админ (public schema) видит только управление системой

---

## Настройка hosts файла

Для локального тестирования добавьте в `C:\Windows\System32\drivers\etc\hosts`:

```
127.0.0.1 localhost
127.0.0.1 tenant1.localhost
127.0.0.1 tenant2.localhost
```

---

## Примеры использования

### JavaScript (Fetch API)

**Логин и получение токена:**
```javascript
const response = await fetch('http://localhost:8000/api/auth/token/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'worker_5', password: 'worker123' })
});
const data = await response.json();
const token = data.access;

// Получить данные пользователя
const userResponse = await fetch('http://localhost:8000/api/users/me/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const user = await userResponse.json();
console.log(user);
```

### Python (Requests)

**Логин и получение токена:**
```python
import requests

response = requests.post(
    'http://localhost:8000/api/auth/token/',
    json={'username': 'worker_5', 'password': 'worker123'}
)
data = response.json()
token = data['access']

# Получить данные пользователя
user_response = requests.get(
    'http://localhost:8000/api/users/me/',
    headers={'Authorization': f'Bearer {token}'}
)
user = user_response.json()
print(user)
```

---

## Дополнительная информация

- Для подробной информации об API авторизации см. `AUTH_API.md`
- Для информации о доступе к тенантам см. `TENANT_ACCESS.md`
- Токены действительны 1 час (ACCESS_TOKEN_LIFETIME)
- Refresh токены действительны 7 дней (REFRESH_TOKEN_LIFETIME)
