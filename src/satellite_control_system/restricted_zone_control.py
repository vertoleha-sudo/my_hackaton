from queue import Empty

from src.system.custom_process import BaseCustomProcess
from src.system.event_types import Event
from src.system.config import ORBIT_DRAWER_QUEUE_NAME, OPTICS_CONTROL_QUEUE_NAME
from src.satellite_control_system.restricted_zone import RestrictedZone


class RestrictedZoneControl(BaseCustomProcess):
    """ Модуль управления запрещёнными зонами """

    def __init__(self, queues_dir):
        super().__init__(
            log_prefix="[ZONE]",
            queues_dir=queues_dir,
            events_q_name="restricted_zone_control",
            event_source_name="restricted_zone_control"
        )
        self._zones: dict[int, RestrictedZone] = {}

    def run(self):
        self._log_message(20, "RestrictedZoneControl запущен")

        while not self._quit:
            self._check_events_q()
            self._check_control_q()

    def _check_events_q(self):
        while True:
            try:
                event: Event = self._events_q.get_nowait()

                if event.operation == "add_zone":
                    self._add_zone(event)

                elif event.operation == "remove_zone":
                    self._remove_zone(event)

            except Empty:
                break

    def _add_zone(self, event: Event):
        zone_id, lat1, lon1, lat2, lon2 = event.parameters

        if zone_id in self._zones:
            self._log_message(10, f"зона {zone_id} уже существует")
            return

        zone = RestrictedZone(zone_id, lat1, lon1, lat2, lon2)
        self._zones[zone_id] = zone

        # отрисовка зоны
        drawer_q = self._queues_dir.get_queue(ORBIT_DRAWER_QUEUE_NAME)
        if drawer_q:
            drawer_q.put(
                Event(
                    source=self._event_source_name,
                    destination=ORBIT_DRAWER_QUEUE_NAME,
                    operation="draw_restricted_zone",
                    parameters=zone
                )
            )

        # 🔐 синхронизация зон с OpticsControl
        optics_q = self._queues_dir.get_queue(OPTICS_CONTROL_QUEUE_NAME)
        if optics_q:
            optics_q.put(
                Event(
                    source=self._event_source_name,
                    destination=OPTICS_CONTROL_QUEUE_NAME,
                    operation="sync_zones",
                    parameters=list(self._zones.values())
                )
            )

        self._log_message(20, f"добавлена зона {zone_id}")

    def _remove_zone(self, event: Event):
        zone_id = event.parameters

        if zone_id not in self._zones:
            self._log_message(10, f"зона {zone_id} не найдена")
            return

        del self._zones[zone_id]

        drawer_q = self._queues_dir.get_queue(ORBIT_DRAWER_QUEUE_NAME)
        if drawer_q:
            drawer_q.put(
                Event(
                    source=self._event_source_name,
                    destination=ORBIT_DRAWER_QUEUE_NAME,
                    operation="clear_restricted_zone",
                    parameters=zone_id
                )
            )

        optics_q = self._queues_dir.get_queue(OPTICS_CONTROL_QUEUE_NAME)
        if optics_q:
            optics_q.put(
                Event(
                    source=self._event_source_name,
                    destination=OPTICS_CONTROL_QUEUE_NAME,
                    operation="sync_zones",
                    parameters=list(self._zones.values())
                )
            )

        self._log_message(20, f"удалена зона {zone_id}")