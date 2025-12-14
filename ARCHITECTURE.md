# Архитектура кибериммунной системы управления спутником

## Обзор

Система реализует кибериммунный подход к безопасности, где все взаимодействия между компонентами контролируются монитором безопасности через явные политики безопасности.

## Принципы архитектуры

1. **Монитор безопасности**: Все взаимодействия между компонентами проходят через монитор безопасности
2. **Политики безопасности**: Явные политики определяют разрешённые взаимодействия
3. **Разделение доменов**: Компоненты разделены на доверенные и недоверенные домены
4. **Классификация данных**: Данные классифицируются по уровню целостности (высокоцелостные/низкоцелостные)

## Классификация доменов

### Доверенные домены (Trusted Domains)

Компоненты, которые управляют критическими данными и операциями:

- **OrbitControl**: Управление параметрами орбиты спутника
- **RestrictedZoneControl**: Управление запрещёнными зонами для съёмки
- **OpticsControl**: Контроль съёмки с проверкой запрещённых зон
- **SecurityMonitor**: Монитор безопасности (критический компонент)

### Недоверенные домены (Untrusted Domains)

Компоненты, которые могут быть скомпрометированы:

- **UserProgramExecutor**: Исполнитель пользовательских программ
- **Satellite**: Симулятор спутника
- **Camera**: Симулятор камеры
- **OrbitDrawer**: Визуализация данных

## Классификация данных

### Высокоцелостные данные (High Integrity / Sensitive)

Данные, которые критичны для безопасности системы:

- **Параметры орбиты**: altitude, raan, inclination
- **Координаты запрещённых зон**: lat1, lon1, lat2, lon2
- **Идентификаторы зон**: zone_id

**Защита**: 
- Изменение только через авторизованные компоненты
- Проверка валидности данных (границы орбиты)
- Все операции проходят через монитор безопасности

### Низкоцелостные данные (Low Integrity / Public)

Данные, которые могут быть публичными:

- **Снимки**: координаты и изображения
- **Визуализация орбиты**: траектория спутника на карте
- **Видеопоток**: данные с камеры

**Защита**:
- Проверка на наличие в запрещённых зонах перед отображением
- Фильтрация через OpticsControl

## Диаграмма потоков данных

```
┌─────────────────────────────────────────────────────────────────┐
│                    SecurityMonitor (Trusted)                   │
│              Все события проходят через монитор                  │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ UserProgram   │  │ OrbitControl  │  │ RestrictedZone│
│ Executor      │  │ (Trusted)     │  │ Control       │
│ (Untrusted)   │  │               │  │ (Trusted)     │
└───────────────┘  └───────────────┘  └───────────────┘
        │                   │                   │
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   Camera      │  │   Satellite   │  │ OpticsControl │
│ (Untrusted)   │  │ (Untrusted)  │  │ (Trusted)     │
└───────────────┘  └───────────────┘  └───────────────┘
        │                   │                   │
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐
│ OrbitDrawer   │
│ (Untrusted)   │
└───────────────┘
```

## Потоки данных

### Поток 1: Изменение орбиты (Высокоцелостные данные)

```
UserProgramExecutor (нет прав) → SecurityMonitor → ❌ БЛОКИРОВКА
UserProgramExecutor (есть права) → SecurityMonitor → OrbitControl → SecurityMonitor → Satellite
```

**Политики безопасности**:
- `SecurityPolicy("user_program", "orbit_control", "change_orbit")`
- `SecurityPolicy("orbit_control", "satellite", "change_orbit")`

**Валидация**:
- OrbitControl проверяет границы орбиты: 200_000 ≤ altitude ≤ 2_000_000

### Поток 2: Создание снимка (Низкоцелостные данные)

```
UserProgramExecutor → SecurityMonitor → Camera → SecurityMonitor → Satellite
                                                                    │
                                                                    ▼
Satellite → SecurityMonitor → Camera → SecurityMonitor → OpticsControl
                                                          │
                                                          ▼ (проверка зон)
                                                    OrbitDrawer
```

**Политики безопасности**:
- `SecurityPolicy("user_program", "camera", "request_photo")`
- `SecurityPolicy("camera", "satellite", "post_camera_coords")`
- `SecurityPolicy("satellite", "camera", "camera_update")`
- `SecurityPolicy("camera", "optics_control", "post_photo")`
- `SecurityPolicy("optics_control", "orbit_drawer", "update_photo_map")`

**Проверка**: OpticsControl проверяет координаты снимка на наличие в запрещённых зонах

### Поток 3: Управление запрещёнными зонами (Высокоцелостные данные)

```
UserProgramExecutor → SecurityMonitor → RestrictedZoneControl
                                              │
                                              ├─→ SecurityMonitor → OpticsControl (sync_zones)
                                              └─→ SecurityMonitor → OrbitDrawer (draw_restricted_zone)
```

**Политики безопасности**:
- `SecurityPolicy("user_program", "restricted_zone_control", "add_zone")`
- `SecurityPolicy("user_program", "restricted_zone_control", "remove_zone")`
- `SecurityPolicy("restricted_zone_control", "optics_control", "sync_zones")`
- `SecurityPolicy("restricted_zone_control", "orbit_drawer", "draw_restricted_zone")`

**Синхронизация**: RestrictedZoneControl автоматически синхронизирует список зон с OpticsControl

### Поток 4: Визуализация орбиты (Низкоцелостные данные)

```
OrbitDrawer → SecurityMonitor → Satellite → SecurityMonitor → OrbitDrawer
```

**Политики безопасности**:
- `SecurityPolicy("orbit_drawer", "satellite", "send_data")`
- `SecurityPolicy("satellite", "orbit_drawer", "update_orbit_data")`

## Политики безопасности

Все политики определены в функции `create_security_policies()` в `example_3.py`.

### Политики для UserProgramExecutor

```python
SecurityPolicy("user_program", "orbit_control", "change_orbit")      # Высокоцелостные
SecurityPolicy("user_program", "camera", "request_photo")             # Низкоцелостные
SecurityPolicy("user_program", "restricted_zone_control", "add_zone") # Высокоцелостные
SecurityPolicy("user_program", "restricted_zone_control", "remove_zone") # Высокоцелостные
```

### Политики для RestrictedZoneControl

```python
SecurityPolicy("restricted_zone_control", "optics_control", "sync_zones")           # Высокоцелостные
SecurityPolicy("restricted_zone_control", "orbit_drawer", "draw_restricted_zone")   # Визуализация
SecurityPolicy("restricted_zone_control", "orbit_drawer", "clear_restricted_zone")  # Визуализация
```

### Политики для OrbitControl

```python
SecurityPolicy("orbit_control", "satellite", "change_orbit")  # Высокоцелостные
```

### Политики для OpticsControl

```python
SecurityPolicy("optics_control", "camera", "request_photo")              # Низкоцелостные
SecurityPolicy("optics_control", "orbit_drawer", "update_photo_map")  # Низкоцелостные
```

### Политики для Camera

```python
SecurityPolicy("camera", "satellite", "post_camera_coords")    # Низкоцелостные
SecurityPolicy("camera", "optics_control", "post_photo")       # Низкоцелостные
```

### Политики для Satellite

```python
SecurityPolicy("satellite", "orbit_drawer", "update_orbit_data")  # Низкоцелостные (визуализация)
SecurityPolicy("satellite", "camera", "camera_update")            # Низкоцелостные
```

### Политики для OrbitDrawer

```python
SecurityPolicy("orbit_drawer", "satellite", "send_data")  # Низкоцелостные
```

## Механизмы защиты

### 1. Монитор безопасности

**Функции**:
- Проверка всех событий на соответствие политикам безопасности
- Блокировка неавторизованных операций
- Логирование всех операций

**Реализация**: `MySecurityMonitor` в `src/example/my_security_monitor.py`

### 2. Контроль доступа

**Функции**:
- Проверка прав пользователя перед выполнением операций
- Три типа прав: `photo`, `orbit`, `zones`

**Реализация**: `UserProgramExecutor` проверяет права в методах `_handle_*`

### 3. Валидация данных

**Функции**:
- Проверка границ орбиты (200_000 - 2_000_000 метров)
- Проверка координат снимков на наличие в запрещённых зонах

**Реализация**: 
- `OrbitControl._check_orbit_bounds()`
- `OpticsControl._is_restricted()`

### 4. Изоляция доменов

**Функции**:
- Разделение на доверенные и недоверенные домены
- Все взаимодействия проходят через монитор безопасности

**Реализация**: Архитектура системы с явным разделением доменов

## Команды пользователя

### ORBIT <altitude> <raan> <inclination>

Изменение параметров орбиты спутника.

**Права**: `orbit`

**Поток данных**:
1. UserProgramExecutor проверяет права
2. Отправка через SecurityMonitor → OrbitControl
3. OrbitControl валидирует границы орбиты
4. Отправка через SecurityMonitor → Satellite

### MAKE_PHOTO

Создание снимка текущей точки на поверхности земли.

**Права**: `photo`

**Поток данных**:
1. UserProgramExecutor проверяет права
2. Отправка через SecurityMonitor → Camera
3. Camera запрашивает координаты у Satellite
4. Camera отправляет снимок в OpticsControl
5. OpticsControl проверяет зоны
6. Если зона разрешена → отображение на карте

### ADD_ZONE <id> <lat1> <lon1> <lat2> <lon2>

Создание запрещённой зоны для съёмки.

**Права**: `zones`

**Поток данных**:
1. UserProgramExecutor проверяет права
2. Отправка через SecurityMonitor → RestrictedZoneControl
3. RestrictedZoneControl создаёт зону
4. Синхронизация с OpticsControl и OrbitDrawer

### REMOVE_ZONE <id>

Удаление запрещённой зоны.

**Права**: `zones`

**Поток данных**:
1. UserProgramExecutor проверяет права
2. Отправка через SecurityMonitor → RestrictedZoneControl
3. RestrictedZoneControl удаляет зону
4. Синхронизация с OpticsControl и OrbitDrawer

## Выводы

Архитектура системы реализует кибериммунный подход через:

1. ✅ **Централизованный монитор безопасности**: Все взаимодействия контролируются
2. ✅ **Явные политики безопасности**: Чёткое определение разрешённых операций
3. ✅ **Разделение доменов**: Изоляция доверенных и недоверенных компонентов
4. ✅ **Классификация данных**: Разделение на высокоцелостные и низкоцелостные данные
5. ✅ **Многоуровневая защита**: Контроль доступа + валидация + монитор безопасности

Система обеспечивает защиту от основных угроз через многоуровневую систему проверок и изоляцию компонентов.

