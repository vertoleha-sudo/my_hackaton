from queue import Empty

from src.system.custom_process import BaseCustomProcess
from src.system.queues_dir import QueuesDirectory
from src.system.event_types import Event, ControlEvent
from src.system.config import (
    LOG_DEBUG,
    LOG_ERROR,
    LOG_INFO,
    DEFAULT_LOG_LEVEL,
    ORBIT_CONTROL_QUEUE_NAME,
    SECURITY_MONITOR_QUEUE_NAME
)


class OrbitControl(BaseCustomProcess):
    """ Модуль корректировки орбиты """

    log_prefix = "[ORBIT]"
    event_source_name = ORBIT_CONTROL_QUEUE_NAME
    events_q_name = event_source_name

    def __init__(
        self,
        queues_dir: QueuesDirectory,
        log_level: int = DEFAULT_LOG_LEVEL
    ):
        super().__init__(
            log_prefix=self.log_prefix,
            queues_dir=queues_dir,
            events_q_name=self.events_q_name,
            event_source_name=self.event_source_name,
            log_level=log_level
        )

        self._log_message(LOG_INFO, "модуль контроля орбиты создан")

    def run(self):
        self._log_message(LOG_INFO, "модуль управления орбитой активен")

        while not self._quit:
            try:
                self._check_events_q()
                self._check_control_q()
            except Exception as e:
                self._log_message(LOG_ERROR, f"ошибка OrbitControl: {e}")

    def _check_orbit_bounds(self, altitude, raan, inclination) -> bool:
        return 200_000 <= altitude <= 2_000_000

    def _check_events_q(self):
        while True:
            try:
                event: Event = self._events_q.get_nowait()

                if not isinstance(event, Event):
                    return

                if event.operation == "change_orbit":
                    altitude, raan, inclination = event.parameters
                    self._log_message(
                        LOG_INFO,
                        "получены новые параметры орбиты"
                    )
                    self._change_orbit(altitude, raan, inclination)

            except Empty:
                break

    def _change_orbit(self, altitude, raan, inclination):
        if not self._check_orbit_bounds(altitude, raan, inclination):
            self._log_message(LOG_ERROR, "орбита вне допустимых границ")
            return

        # Отправляем через монитор безопасности
        security_q = self._queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
        if security_q:
            security_q.put(
                Event(
                    source=self._event_source_name,
                    destination="satellite",
                    operation="change_orbit",
                    parameters=[altitude, raan, inclination]
                )
            )
            self._log_message(
                LOG_INFO,
                "команда смены орбиты отправлена через монитор безопасности"
            )
