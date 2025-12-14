import numpy as np
from time import sleep

from src.satellite_simulator.satellite import Satellite
from src.satellite_simulator.orbit_drawer import OrbitDrawer
from src.satellite_simulator.camera import Camera

from src.satellite_control_system.optics_control import OpticsControl
from src.satellite_control_system.orbit_control import OrbitControl
from src.satellite_control_system.restricted_zone_control import RestrictedZoneControl

from src.system.queues_dir import QueuesDirectory
from src.system.system_wrapper import SystemComponentsContainer
from src.system.event_types import Event
from src.system.config import LOG_DEBUG


if __name__ == "__main__":
    queues_dir = QueuesDirectory()

    satellite = Satellite(
        altitude=1000e3,
        position_angle=0,
        inclination=np.pi / 3,
        raan=0,
        queues_dir=queues_dir,
        log_level=LOG_DEBUG
    )

    camera = Camera(queues_dir=queues_dir, log_level=LOG_DEBUG)
    drawer = OrbitDrawer(queues_dir=queues_dir, log_level=LOG_DEBUG)

    optics = OpticsControl(queues_dir=queues_dir, log_level=LOG_DEBUG)
    orbit_control = OrbitControl(queues_dir=queues_dir, log_level=LOG_DEBUG)
    zone_control = RestrictedZoneControl(queues_dir=queues_dir)

    system = SystemComponentsContainer(
        components=[
            satellite,
            camera,
            drawer,
            optics,
            orbit_control,
            zone_control
        ],
        log_level=LOG_DEBUG
    )

    system.start()
    sleep(3)

    print("\n=== ДОБАВЛЯЕМ ЗАПРЕЩЕННУЮ ЗОНУ ===\n")
    zone_q = queues_dir.get_queue("restricted_zone_control")
    zone_q.put(
        Event(
            source=None,
            destination="restricted_zone_control",
            operation="add_zone",
            parameters=[1, 25, 155, 35, 165]
        )
    )

    sleep(2)

    print("\n=== ПОПЫТКА ВЫВЕСТИ СПУТНИК НА ЗАПРЕЩЁННУЮ ОРБИТУ ===\n")
    orbit_q = queues_dir.get_queue("orbit_control")
    orbit_q.put(
        Event(
            source=None,
            destination="orbit_control",
            operation="change_orbit",
            parameters=[50_000, 0, 0]  # ❌ запрещено
        )
    )

    sleep(2)

    print("\n=== ПОПЫТКА СДЕЛАТЬ СНИМКИ В ЗАПРЕЩЕННОЙ ЗОНЕ ===\n")
    cam_q = queues_dir.get_queue("camera")
    for _ in range(6):
        cam_q.put(
            Event(
                source=None,
                destination="camera",
                operation="request_photo",
                parameters=None
            )
        )
        sleep(0.5)

    sleep(5)

    system.stop()
    system.clean()
