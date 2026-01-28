# API Авторизации

## Обзор

API авторизации обеспечивает управление пользователями и выдачу JWT токенов для мобильных приложений. Каждый тенант имеет своих собственных пользователей, полностью изолированных друг от друга.

## Структура пользователей

### Роли

- **ADMIN** — администратор тенанта (может входить в админ-панель)
- **WORKER** — работник (может использовать мобильное приложение)

### Изоляция

Пользователи хранятся в схеме конкретного тенанта и не видны другим тенантам:
- Админ Tenant 1 не может логиниться в Tenant 2
- Каждый тенант имеет своих админов и работников

## Endpoints

### 1. Получить токен

**POST** `/api/auth/token/`

Получить JWT токен для авторизации.

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

**Response (401):**
```json
{
  "detail": "No active account found with the given credentials"
}
```

### 2. Получить данные текущего пользователя

**GET** `/api/users/me/`

Получить информацию о текущем авторизованном пользователе.

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

**Response (401):**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 3. Регистрация пользователя

**POST** `/api/users/register/`

Создать нового пользователя (только для работников).

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

## Примеры использования

### cURL

```bash
# Получить токен
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"worker_5","password":"worker123"}'

# Получить данные пользователя
curl -X GET http://localhost:8000/api/users/me/ \
  -H "Authorization: Bearer <access_token>"
```

### Python (requests)

```python
import requests

# Логин
response = requests.post(
    'http://localhost:8000/api/auth/token/',
    json={'username': 'worker_5', 'password': 'worker123'}
)
data = response.json()
token = data['access']

# Получить данные пользователя
response = requests.get(
    'http://localhost:8000/api/users/me/',
    headers={'Authorization': f'Bearer {token}'}
)
user = response.json()
print(user)
```

### JavaScript (fetch)

```javascript
// Логин
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

## Тестовые учетные данные

### Tenant 1 (tenant1.localhost)
- **Админ:** admin_5 / admin123
- **Работник:** worker_5 / worker123

### Tenant 2 (tenant2.localhost)
- **Админ:** admin_6 / admin123
- **Работник:** worker_6 / worker123

## Безопасность

- Токены действительны 1 час (ACCESS_TOKEN_LIFETIME)
- Refresh токены действительны 7 дней (REFRESH_TOKEN_LIFETIME)
- Пароли хешируются с использованием PBKDF2
- Каждый тенант полностью изолирован на уровне БД

## Создание пользователей

Для создания пользователей для всех тенантов используйте скрипт:

```bash
python create_users_simple.py
```

Скрипт автоматически создаст админа и работника для каждого тенанта.
