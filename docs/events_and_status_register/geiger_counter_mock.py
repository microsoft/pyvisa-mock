from typing import List, Optional
from enum import Enum
from threading import RLock, Event, Thread
import sched
import time
from random import gauss

from visa_mock.base.base_mocker import BaseMocker, scpi


class MessageCode(Enum):
    EXPOSURE_LIMIT_EXCEEDED = 0x01
    READING_LIMIT_EXCEEDED = 0x02
    REQUEST_SERVICE = 0x40


class GeigerCounterMock(BaseMocker):
    """

    Mock a visa inst Geiger counter that supports a threshold detection of exposure rate.

    """

    _reading_period = .100  # Read every x seconds
    _reading_mean = 0
    _reading_std = .1

    def __init__(self, call_delay: float = 0):
        super().__init__(call_delay=call_delay)
        self._readings: List[float] = []
        self._accumulation = 0.0
        self._exposure_threshold = 0.0
        self._reading_threshold = 0.0
        self._lock = RLock()
        self._running = Event()
        self._running.clear()
        self._cur_reading_time = time.time()
        self._measurement_scheduler = sched.scheduler(time.time, time.sleep)
        self._sched_thread: Optional[Thread] = None

    @property
    def next_reading_time(self) -> float:
        self._cur_reading_time += self._reading_period
        return self._cur_reading_time

    def _take_reading(self):
        """
        Task should be run in a thread to periodically make readings.
        """
        cur_reading = abs(gauss(self._reading_mean, self._reading_std))
        with self._lock:
            set_service_request = False
            self._readings.append(cur_reading)
            self._accumulation += cur_reading
            if self._reading_threshold != 0:
                if cur_reading > self._reading_threshold:
                    if not self.stb & MessageCode.READING_LIMIT_EXCEEDED.value:
                        self.stb |= MessageCode.READING_LIMIT_EXCEEDED.value
                        set_service_request = True
            if self._exposure_threshold != 0:
                if self._accumulation > self._exposure_threshold:
                    if not self.stb & MessageCode.EXPOSURE_LIMIT_EXCEEDED.value:
                        self.stb |= MessageCode.EXPOSURE_LIMIT_EXCEEDED.value
                        set_service_request = True
            if set_service_request:
                if not self.stb & MessageCode.REQUEST_SERVICE.value:
                    self.stb |= MessageCode.REQUEST_SERVICE.value
                    self.set_service_request_event()
        if self._running.is_set():
            self._measurement_scheduler.enterabs(
                time=self.next_reading_time,
                priority=1,
                action=self._take_reading,
                argument=[])

    @scpi(r'\*IDN\?')
    def identify(self) -> str:
        return'geiger counter:fake corp:123456'

    @scpi(r'\*CLS')
    def clear_stb(self) -> None:
        with self._lock:
            self.stb = 0

    @scpi(r'ALERT:EXPOSURE:THRESHOLD (.*)')
    def set_exposure_threshold(self, threshold: float) -> None:
        with self._lock:
            self._exposure_threshold = threshold

    @scpi(r'ALERT:EXPOSURE:THRESHOLD\?')
    def get_exposure_threshold(self) -> float:
        return self._exposure_threshold

    @scpi(r'ALERT:READING:THRESHOLD (.*)')
    def set_reading_threshold(self, threshold: float) -> None:
        with self._lock:
            self._reading_threshold = threshold

    @scpi(r'ALERT:READING:THRESHOLD\?')
    def get_reading_threshold(self) -> float:
        return self._reading_threshold

    @scpi(r'MEAS:READING\?')
    def get_last_reading(self) -> float:
        return self._readings[-1]

    @scpi(r'MEAS:EXPOSURE\?')
    def get_exposure(self) -> float:
        return self._accumulation

    @scpi(r'MEAS:EXPOSURE:RESET')
    def reset_exposure(self) -> None:
        with self._lock:
            self._accumulation = 0
            self.stb &= ~MessageCode.EXPOSURE_LIMIT_EXCEEDED.value

    @scpi(r'MEAS:START')
    def start_measurements(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._cur_reading_time = time.time()
        self._take_reading()
        self._sched_thread = Thread(
            target=self._measurement_scheduler.run,
            # Should be okay to kill thread on exit, no resouces open
            daemon=True)
        self._sched_thread.start()

    @scpi(r'MEAS:STOP')
    def stop_measurements(self) -> None:
        self._running.clear()
        if self._sched_thread is not None:
            self._sched_thread.join()
        self._sched_thread = None
