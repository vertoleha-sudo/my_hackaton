from queue import Empty

from src.system.custom_process import BaseCustomProcess
from src.system.event_types import Event
from src.system.config import (
    ORBIT_DRAWER_QUEUE_NAME,
    OPTICS_CONTROL_QUEUE_NAME,
    SECURITY_MONITOR_QUEUE_NAME,
    LOG_INFO,
    DEFAULT_LOG_LEVEL
)
from src.satellite_control_system.restricted_zone import RestrictedZone


class RestrictedZoneControl(BaseCustomProcess):
    """ Модуль управления запрещёнными зонами """

    def __init__(self, queues_dir, log_level=DEFAULT_LOG_LEVEL):
        super().__init__(
            log_prefix="[ZONE]",
            queues_dir=queues_dir,
            events_q_name="restricted_zone_control",
            event_source_name="restricted_zone_control",
            log_level=log_level
        )
        self._zones: dict[int, RestrictedZone] = {}

    def run(self):
        self._log_message(LOG_INFO, "RestrictedZoneControl запущен")

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
            self._log_message(LOG_INFO, f"зона {zone_id} уже существует")
            return

        zone = RestrictedZone(zone_id, lat1, lon1, lat2, lon2)
        self._zones[zone_id] = zone

        # Отправляем через монитор безопасности: отрисовка зоны
        security_q = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
        if security_q:
            security_q.put(
                Event(
                    source=self._event_source_name,
                    destination=ORBIT_DRAWER_QUEUE_NAME,
                    operation="draw_restricted_zone",
                    parameters=zone
                )
            )

        # Отправляем через монитор безопасности: синхронизация зон с OpticsControl
        if security_q:
            security_q.put(
                Event(
                    source=self._event_source_name,
                    destination=OPTICS_CONTROL_QUEUE_NAME,
                    operation="sync_zones",
                    parameters=list(self._zones.values())
                )
            )

        self._log_message(LOG_INFO, f"добавлена зона {zone_id}")

    def _remove_zone(self, event: Event):
        zone_id = event.parameters

        if zone_id not in self._zones:
            self._log_message(LOG_INFO, f"зона {zone_id} не найдена")
            return

        del self._zones[zone_id]

        # Отправляем через монитор безопасности: очистка зоны
        security_q = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
        if security_q:
            security_q.put(
                Event(
                    source=self._event_source_name,
                    destination=ORBIT_DRAWER_QUEUE_NAME,
                    operation="clear_restricted_zone",
                    parameters=zone_id
                )
            )

        # Отправляем через монитор безопасности: синхронизация зон
        if security_q:
            security_q.put(
                Event(
                    source=self._event_source_name,
                    destination=OPTICS_CONTROL_QUEUE_NAME,
                    operation="sync_zones",
                    parameters=list(self._zones.values())
                )
            )

        self._log_message(LOG_INFO, f"удалена зона {zone_id}")