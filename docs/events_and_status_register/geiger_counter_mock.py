from typing import List
from enum import Enum
from threading import RLock, Event
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

    _reading_mean = 1
    _reading_std = 1000
    _reading_period = .100  # Read every x seconds

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

    @property
    def next_reading_time(self) -> float:
        self._cur_reading_time += self._reading_period
        return self._cur_reading_time

    def _take_reading(self):
        """
        Task should be run in a thread to periodically make readings.
        """
        cur_reading = gauss(self._reading_mean, self._reading_std)
        stb = 0
        with self._lock:
            self._readings.append(cur_reading)
            self._accumulation += cur_reading
            if self._reading_threshold != 0 and cur_reading > self._reading_threshold:
                stb |= MessageCode.READING_LIMIT_EXCEEDED
            if self._exposure_threshold != 0 and self._accumulation > self._exposure_threshold:
                stb |= MessageCode.EXPOSURE_LIMIT_EXCEEDED
            if stb != 0:
                stb |= MessageCode.REQUEST_SERVICE
                self.set_service_request_event()
        if self._running.is_set():
            self._measurement_scheduler.enterabs(
                time=self.next_reading_time,
                priority=1,
                action=self._take_reading,
                arguments=(self))

    @scpi(r'\*IDN\?')
    def set_exposure_threshold(self) -> str:
        return'geiger counter:fake corp:123456'

    @scpi(r'ALERT:EXPOSURE:THRESHOLD (.*)')
    def set_exposure_threshold(self, threshold: float) -> None:
        with self._lock:
            self._exposure_threshold = threshold

    @scpi(r'ALERT:EXPOSURE:THRESHOLD?')
    def get_exposure_threshold(self) -> float:
        return self._exposure_threshold

    @scpi(r'ALERT:READING:THRESHOLD (.*)')
    def set_reading_threshold(self, threshold: float) -> None:
        with self._lock:
            self._exposure_threshold = threshold

    @scpi(r'ALERT:READING:THRESHOLD?')
    def get_reading_threshold(self) -> float:
        return self._reading_threshold

    @scpi(r'MEAS:READING?')
    def get_last_reading(self) -> float:
        return self._readings[-1]

    @scpi(r'MEAS:EXPOSURE?')
    def get_exposure(self) -> float:
        return self._accumulation

    @scpi(r'MEAS:START')
    def start_measurements(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._cur_reading_time = time.time()
        self._take_reading()

    @scpi(r'MEAS:STOP')
    def stop_measurements(self) -> None:
        self._running.clear()
        while not self._measurement_scheduler.empty:
            time.sleep(self._reading_period)
