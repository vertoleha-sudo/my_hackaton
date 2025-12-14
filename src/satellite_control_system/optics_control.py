from queue import Empty

from src.system.custom_process import BaseCustomProcess
from src.system.event_types import Event
from src.system.config import (
    LOG_DEBUG,
    LOG_ERROR,
    LOG_INFO,
    DEFAULT_LOG_LEVEL,
    OPTICS_CONTROL_QUEUE_NAME,
    ORBIT_DRAWER_QUEUE_NAME,
    SECURITY_MONITOR_QUEUE_NAME
)


class OpticsControl(BaseCustomProcess):
    """ Модуль управления оптикой с проверкой запрещённых зон """

    log_prefix = "[OPTIC]"
    event_source_name = OPTICS_CONTROL_QUEUE_NAME
    events_q_name = OPTICS_CONTROL_QUEUE_NAME

    def __init__(self, queues_dir, log_level=DEFAULT_LOG_LEVEL):
        super().__init__(
            log_prefix=self.log_prefix,
            queues_dir=queues_dir,
            events_q_name=self.events_q_name,
            event_source_name=self.event_source_name,
            log_level=log_level
        )

        self._zones = []
        self._log_message(LOG_INFO, "модуль управления оптикой создан")

    def run(self):
        self._log_message(LOG_INFO, "модуль управления оптикой активен")

        while not self._quit:
            try:
                self._check_events_q()
                self._check_control_q()
            except Exception as e:
                self._log_message(LOG_ERROR, f"ошибка OpticsControl: {e}")

    def _check_events_q(self):
        while True:
            try:
                event: Event = self._events_q.get_nowait()

                if event.operation == "request_photo":
                    self._request_photo()

                elif event.operation == "post_photo":
                    lat, lon = event.parameters

                    if self._is_restricted(lat, lon):
                        self._log_message(
                            LOG_ERROR,
                            f"съёмка ({lat:.2f}, {lon:.2f}) запрещена зоной"
                        )
                        return

                    # Отправляем через монитор безопасности
                    security_q = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
                    if security_q:
                        security_q.put(
                            Event(
                                source=self._event_source_name,
                                destination=ORBIT_DRAWER_QUEUE_NAME,
                                operation="update_photo_map",
                                parameters=(lat, lon)
                            )
                        )
                        self._log_message(
                            LOG_DEBUG,
                            f"рисуем снимок ({lat:.2f}, {lon:.2f})"
                        )

                elif event.operation == "sync_zones":
                    self._zones = event.parameters
                    self._log_message(
                        LOG_INFO,
                        f"обновлены запрещённые зоны: {len(self._zones)}"
                    )

            except Empty:
                break

    def _request_photo(self):
        # Отправляем через монитор безопасности
        security_q = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
        if security_q:
            security_q.put(
                Event(
                    source=self._event_source_name,
                    destination="camera",
                    operation="request_photo",
                    parameters=None
                )
            )
            self._log_message(LOG_DEBUG, "запрос фото отправлен через монитор безопасности")

    def _is_restricted(self, lat, lon) -> bool:
        return any(zone.contains(lat, lon) for zone in self._zones)
