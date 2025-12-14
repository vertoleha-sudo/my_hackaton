from queue import Empty

from src.system.custom_process import BaseCustomProcess
from src.system.event_types import Event
from src.system.config import (
    LOG_INFO,
    LOG_ERROR,
    DEFAULT_LOG_LEVEL,
    SECURITY_MONITOR_QUEUE_NAME
)


class UserProgramExecutor(BaseCustomProcess):
    """
    Исполнитель пользовательских программ.
    """

    def __init__(self, queues_dir, permissions, log_level=DEFAULT_LOG_LEVEL):
        super().__init__(
            log_prefix="[USER]",
            queues_dir=queues_dir,
            events_q_name="user_program",
            event_source_name="user_program",
            log_level=log_level
        )
        self._permissions = permissions
        self._log_message(LOG_INFO, "модуль пользователя создан")

    def run(self):
        self._log_message(LOG_INFO, "исполнитель пользовательских программ запущен")
        while not self._quit:
            self._check_events_q()
            self._check_control_q()

    def _check_events_q(self):
        while True:
            try:
                event = self._events_q.get_nowait()
                command = event.operation
                params = event.parameters

                if command == "ORBIT":
                    self._handle_orbit(params)
                elif command == "MAKE_PHOTO":
                    self._handle_photo()
                elif command == "ADD_ZONE":
                    self._handle_add_zone(params)
                elif command == "REMOVE_ZONE":
                    self._handle_remove_zone(params)

            except Empty:
                break

    def _handle_orbit(self, params):
        if "orbit" not in self._permissions:
            self._log_message(LOG_ERROR, "нет прав на изменение орбиты")
            return

        # Отправляем через монитор безопасности
        security_q = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
        if security_q:
            security_q.put(
                Event(
                    source=self._event_source_name,
                    destination="orbit_control",
                    operation="change_orbit",
                    parameters=params
                )
            )

    def _handle_photo(self):
        if "photo" not in self._permissions:
            self._log_message(LOG_ERROR, "нет прав на создание снимков")
            return

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

    def _handle_add_zone(self, params):
        if "zones" not in self._permissions:
            self._log_message(LOG_ERROR, "нет прав на редактирование зон")
            return

        # Отправляем через монитор безопасности
        security_q = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
        if security_q:
            security_q.put(
                Event(
                    source=self._event_source_name,
                    destination="restricted_zone_control",
                    operation="add_zone",
                    parameters=params
                )
            )

    def _handle_remove_zone(self, params):
        if "zones" not in self._permissions:
            self._log_message(LOG_ERROR, "нет прав на редактирование зон")
            return

        # Отправляем через монитор безопасности
        security_q = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
        if security_q:
            security_q.put(
                Event(
                    source=self._event_source_name,
                    destination="restricted_zone_control",
                    operation="remove_zone",
                    parameters=params
                )
            )
