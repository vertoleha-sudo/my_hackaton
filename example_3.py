import numpy as np
from time import sleep

from src.satellite_simulator.satellite import Satellite
from src.satellite_simulator.orbit_drawer import OrbitDrawer
from src.satellite_simulator.camera import Camera

from src.satellite_control_system.optics_control import OpticsControl
from src.satellite_control_system.orbit_control import OrbitControl
from src.satellite_control_system.restricted_zone_control import RestrictedZoneControl
from src.satellite_control_system.user_program_executor import UserProgramExecutor

from src.system.queues_dir import QueuesDirectory
from src.system.system_wrapper import SystemComponentsContainer
from src.system.event_types import Event
from src.system.config import LOG_DEBUG, SECURITY_MONITOR_QUEUE_NAME
from src.example.my_security_monitor import MySecurityMonitor
from src.system.security_policy_type import SecurityPolicy


def create_security_policies():
    """
    Создание полного набора политик безопасности системы.
    Политика определяет разрешённые взаимодействия между компонентами.
    
    ВСЕ взаимодействия между компонентами должны проходить через монитор безопасности.
    Монитор проверяет каждое событие на соответствие политикам безопасности.
    
    КЛАССИФИКАЦИЯ ДАННЫХ:
    - Высокоцелостные (sensitive): параметры орбиты, координаты запрещённых зон
    - Низкоцелостные (public): снимки, видеопоток, визуализация орбиты
    """
    return [
        # === Политики для UserProgramExecutor (недоверенный домен) ===
        # Пользовательская программа может отправлять команды через монитор
        # ВАЖНО: права пользователя проверяются в UserProgramExecutor, но монитор
        # дополнительно проверяет разрешённые операции
        SecurityPolicy("user_program", "orbit_control", "change_orbit"),  # Высокоцелостные данные
        SecurityPolicy("user_program", "camera", "request_photo"),  # Низкоцелостные данные
        SecurityPolicy("user_program", "restricted_zone_control", "add_zone"),  # Высокоцелостные данные
        SecurityPolicy("user_program", "restricted_zone_control", "remove_zone"),  # Высокоцелостные данные
        
        # === Политики для RestrictedZoneControl (доверенный домен) ===
        # Контроллер зон может отправлять обновления зон
        # ВАЖНО: RestrictedZoneControl управляет высокоцелостными данными (координаты зон)
        SecurityPolicy("restricted_zone_control", "optics_control", "sync_zones"),  # Высокоцелостные данные
        SecurityPolicy("restricted_zone_control", "orbit_drawer", "draw_restricted_zone"),  # Визуализация
        SecurityPolicy("restricted_zone_control", "orbit_drawer", "clear_restricted_zone"),  # Визуализация
        
        # === Политики для OrbitControl (доверенный домен) ===
        # Контроллер орбиты может управлять спутником
        # ВАЖНО: OrbitControl управляет высокоцелостными данными (параметры орбиты)
        SecurityPolicy("orbit_control", "satellite", "change_orbit"),  # Высокоцелостные данные
        
        # === Политики для OpticsControl (доверенный домен) ===
        # Контроллер оптики может запрашивать фото и обновлять карту
        SecurityPolicy("optics_control", "camera", "request_photo"),  # Низкоцелостные данные
        SecurityPolicy("optics_control", "orbit_drawer", "update_photo_map"),  # Низкоцелостные данные
        
        # === Политики для Camera (недоверенный домен - симулятор) ===
        # Камера может запрашивать координаты у спутника
        SecurityPolicy("camera", "satellite", "post_camera_coords"),  # Низкоцелостные данные
        # Камера может отправлять данные снимка в OpticsControl
        SecurityPolicy("camera", "optics_control", "post_photo"),  # Низкоцелостные данные
        
        # === Политики для Satellite (недоверенный домен - симулятор) ===
        # Спутник может отправлять данные отрисовщику
        SecurityPolicy("satellite", "orbit_drawer", "update_orbit_data"),  # Низкоцелостные данные (визуализация)
        # Спутник может отвечать камере
        SecurityPolicy("satellite", "camera", "camera_update"),  # Низкоцелостные данные
        
        # === Политики для OrbitDrawer (недоверенный домен - визуализация) ===
        # Отрисовщик может запрашивать данные у спутника
        SecurityPolicy("orbit_drawer", "satellite", "send_data"),  # Низкоцелостные данные
    ]


if __name__ == "__main__":
    print("\n" + "="*70)
    print("КИБЕРИММУННАЯ СИСТЕМА УПРАВЛЕНИЯ СПУТНИКОМ")
    print("="*70 + "\n")
    
    # Создаём каталог очередей
    queues_dir = QueuesDirectory()

    # === СОЗДАНИЕ МОНИТОРА БЕЗОПАСНОСТИ ===
    print("📋 Инициализация политик безопасности...")
    security_policies = create_security_policies()
    security_monitor = MySecurityMonitor(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG,
        policies=security_policies
    )
    print(f"✅ Загружено {len(security_policies)} политик безопасности\n")

    # === СОЗДАНИЕ КОМПОНЕНТОВ СИСТЕМЫ ===
    
    # Симуляторы (недоверенный домен)
    satellite = Satellite(
        altitude=1000e3,
        position_angle=0,
        inclination=np.pi / 3,
        raan=0,
        queues_dir=queues_dir,
        log_level=LOG_DEBUG
    )

    camera = Camera(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG
    )

    drawer = OrbitDrawer(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG
    )

    # Контроллеры (доверенные домены)
    optics_control = OpticsControl(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG
    )

    orbit_control = OrbitControl(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG
    )

    zone_control = RestrictedZoneControl(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG
    )

    # Исполнитель пользовательских программ (недоверенный домен)
    # Пользователь имеет ограниченные права
    user_executor = UserProgramExecutor(
        queues_dir=queues_dir,
        permissions={"photo", "zones"},  # НЕТ прав на изменение орбиты!
        log_level=LOG_DEBUG
    )

    # Контейнер всех компонентов
    system = SystemComponentsContainer(
        components=[
            security_monitor,  # Монитор должен быть первым!
            satellite,
            camera,
            drawer,
            optics_control,
            orbit_control,
            zone_control,
            user_executor
        ],
        log_level=LOG_DEBUG
    )

    # === ЗАПУСК СИСТЕМЫ ===
    print("\n🚀 Запуск системы...\n")
    system.start()
    sleep(3)

    # === ДЕМОНСТРАЦИЯ РАБОТЫ СИСТЕМЫ ===
    
    print("\n" + "="*70)
    print("СЦЕНАРИЙ 1: Добавление запрещённой зоны")
    print("="*70 + "\n")
    
    # Пользователь добавляет запрещённую зону (РАЗРЕШЕНО)
    user_q = queues_dir.get_queue("user_program")
    user_q.put(
        Event(
            source=None,  # Внешний источник
            destination="user_program",
            operation="ADD_ZONE",
            parameters=[1, 25, 155, 35, 165]  # Зона над Тихим океаном
        )
    )
    print("👤 Пользователь: добавить запрещённую зону 1")
    sleep(2)

    print("\n" + "="*70)
    print("СЦЕНАРИЙ 2: Попытка изменить орбиту (НЕТ ПРАВ)")
    print("="*70 + "\n")
    
    # Пользователь пытается изменить орбиту (ЗАПРЕЩЕНО - нет прав)
    user_q.put(
        Event(
            source=None,
            destination="user_program",
            operation="ORBIT",
            parameters=[500_000, 0, 0]
        )
    )
    print("👤 Пользователь: изменить орбиту")
    print("❌ Ожидается отказ - у пользователя нет прав на орбиту")
    sleep(2)

    print("\n" + "="*70)
    print("СЦЕНАРИЙ 3: Прямая попытка изменить орбиту (ОБХОД ПРАВ)")
    print("="*70 + "\n")
    
    # Попытка обойти UserExecutor и отправить напрямую
    # Это будет заблокировано монитором безопасности
    orbit_q = queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
    orbit_q.put(
        Event(
            source="unknown_attacker",  # Неизвестный источник
            destination="orbit_control",
            operation="change_orbit",
            parameters=[50_000, 0, 0]
        )
    )
    print("🔴 Атакующий: прямая отправка команды изменения орбиты")
    print("🛡️ Ожидается блокировка монитором безопасности")
    sleep(2)

    print("\n" + "="*70)
    print("СЦЕНАРИЙ 4: Легитимное изменение орбиты от OrbitControl")
    print("="*70 + "\n")
    
    # Добавим временно права на орбиту
    print("🔧 Администратор: выдача временных прав на орбиту")
    user_executor._permissions.add("orbit")
    sleep(0.5)  # Небольшая задержка для применения прав
    
    user_q.put(
        Event(
            source=None,
            destination="user_program",
            operation="ORBIT",
            parameters=[900_000, np.pi/4, np.pi/3]
        )
    )
    print("👤 Пользователь: изменить орбиту (с правами)")
    print("✅ Ожидается успешное выполнение")
    sleep(4)

    print("\n" + "="*70)
    print("СЦЕНАРИЙ 5: Съёмка с проверкой запрещённых зон")
    print("="*70 + "\n")
    
    print("📸 Попытка сделать несколько снимков...")
    for i in range(8):
        user_q.put(
            Event(
                source=None,
                destination="user_program",
                operation="MAKE_PHOTO",
                parameters=None
            )
        )
        sleep(0.7)
    
    print("\n💡 Некоторые снимки могут быть заблокированы из-за запрещённой зоны")
    sleep(3)

    print("\n" + "="*70)
    print("СЦЕНАРИЙ 6: Добавление второй зоны")
    print("="*70 + "\n")
    
    user_q.put(
        Event(
            source=None,
            destination="user_program",
            operation="ADD_ZONE",
            parameters=[2, -30, -60, -10, -40]  # Зона над Южной Америкой
        )
    )
    print("👤 Пользователь: добавить запрещённую зону 2")
    sleep(2)

    print("\n" + "="*70)
    print("СЦЕНАРИЙ 7: Удаление зоны")
    print("="*70 + "\n")
    
    user_q.put(
        Event(
            source=None,
            destination="user_program",
            operation="REMOVE_ZONE",
            parameters=1
        )
    )
    print("👤 Пользователь: удалить зону 1")
    sleep(2)

    print("\n" + "="*70)
    print("СЦЕНАРИЙ 8: Попытка нарушить границы орбиты")
    print("="*70 + "\n")
    
    user_q.put(
        Event(
            source=None,
            destination="user_program",
            operation="ORBIT",
            parameters=[50_000, 0, 0]  # Слишком низкая орбита!
        )
    )
    print("👤 Пользователь: установить опасно низкую орбиту")
    print("🛡️ Ожидается блокировка OrbitControl")
    sleep(2)

    print("\n📊 Наблюдение за системой...")
    sleep(5)

    # === ЗАВЕРШЕНИЕ ===
    print("\n" + "="*70)
    print("ЗАВЕРШЕНИЕ РАБОТЫ СИСТЕМЫ")
    print("="*70 + "\n")
    
    system.stop()
    system.clean()
    
    print("\n✅ Демонстрация завершена!")
    print("\n📝 Продемонстрированные механизмы безопасности:")
    print("   1. ✓ Контроль доступа через права пользователя")
    print("   2. ✓ Проверка всех команд монитором безопасности")
    print("   3. ✓ Блокировка неавторизованных источников")
    print("   4. ✓ Валидация параметров орбиты")
    print("   5. ✓ Контроль запрещённых зон для съёмки")
    print("   6. ✓ Разделение доменов по уровню доверия\n")