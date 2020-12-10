from typing import Dict
from collections import defaultdict
import time
from threading import Thread
from enum import Enum, auto

from visa_mock.base.base_mocker import BaseMocker, scpi, scpi_raw_regex


class Mocker0(BaseMocker):
    """
    A mocker class mocking a multi channel voltage source.
    Voltages are zero by default

    The upper case part in the scpi cmd is mandatory, while the
    lower case potion is optional.
    """

    def __init__(self, call_delay: float = 0.0) -> None:
        super().__init__(call_delay=call_delay)
        self._voltage = defaultdict(lambda: 0.0)

    @scpi(r":INSTRument:CHANNEL(.*):VOLTage (.*)")
    def _set_voltage(self, channel: int, value: float) -> None:
        self._voltage[channel] = value

    @scpi(r":INSTRument:CHANNEL(.*):VOLTage\?")
    def _get_voltage(self, channel: int) -> float:
        return self._voltage[channel]


class Mocker1(BaseMocker):
    """
    A mocker class mocking a multi channel voltage source.
    Voltages are zero by default
    """

    def __init__(self, call_delay: float = 0.0) -> None:
        super().__init__(call_delay=call_delay)
        self._voltage = defaultdict(lambda: 0.0)

    @scpi(r":INSTR:CHANNEL(.*):VOLT (.*)")
    def _set_voltage(self, channel: int, value: float) -> None:
        self._voltage[channel] = value

    @scpi(r":INSTR:CHANNEL(.*):VOLT\?")
    def _get_voltage(self, channel: int) -> float:
        return self._voltage[channel]


class Mocker2(BaseMocker):
    """
    A mocker class mocking a multi channel voltage source.
    Voltages are zero by default
    """

    def __init__(self, call_delay: float = 0.0) -> None:
        super().__init__(call_delay=call_delay)
        self._voltage = defaultdict(lambda: 0.0)

    @scpi(r":INSTR:CHANNEL(.*):VOLT (.*)")
    def _set_voltage(self, channel: int, value: float) -> None:
        self._voltage[channel] = value

    @scpi(r":INSTR:CHANNEL(.*):VOLT\?")
    def _get_voltage(self, channel: int) -> float:
        return 2 * self._voltage[channel]


class MockerChannel(BaseMocker):

    def __init__(self, call_delay: float = 0.0) -> None:
        super().__init__(call_delay=call_delay)
        self._voltage = 0

    @scpi(r":VOLTage (.*)")
    def _set_voltage(self, voltage: float) -> None:
        self._voltage = voltage

    @scpi(r":VOLTage\?")
    def _get_voltage(self) -> float:
        return self._voltage


class Mocker3(BaseMocker):

    def __init__(self, call_delay: float = 0.0) -> None:
        super().__init__(call_delay=call_delay)
        self._channels = {
            1: MockerChannel(),
            2: MockerChannel()
        }

    @scpi(r":CHANNEL(.*)")
    def _channel(self, number: int) -> MockerChannel:
        return self._channels[number]


class Mocker4(BaseMocker):

    def __init__(self, call_delay: float = 0.0) -> None:
        super().__init__(call_delay=call_delay)
        self._instruments = {
            1: Mocker3(),
            2: Mocker3()
        }

    @scpi(r":INSTRument(.*)")
    def _channel(self, number: int) -> Mocker3:
        return self._instruments[number]


class Mocker5(BaseMocker):
    """

    Mock a visa inst that uses status byte and event.

    """

    meas_time: float = 1

    def __init__(self, call_delay: float = 0.0) -> None:
        super().__init__(call_delay=call_delay)
        self._voltage: Dict[int, float] = defaultdict(lambda: 0.0)

    @scpi(r'\*CLS')
    def clear_stb(self) -> None:
        self.stb = 0

    @scpi(r":INSTRument:CHANNEL(.*):VOLTage (.*)")
    def _set_voltage(self, channel: int, value: float) -> None:
        self._voltage[channel] = value

    @scpi(r":INSTRument:CHANNEL(.*):VOLTage\?")
    def _get_voltage(self, channel: int) -> float:
        return self._run_measurement(channel)

    def _run_measurement(self, channel: int) -> float:
        time.sleep(self.meas_time)
        self.stb = 0x40
        self.set_service_request_event()
        return self._voltage[channel]

    @scpi(r":INSTRument:CHANNEL(.*):MEASure")
    def _start_voltage_meas(self, channel: int) -> None:
        if self.stb & 0x40:
            # Don't start another measurement until the previous one is cleared.
            return
        Thread(
            target=self._run_measurement,
            args=(channel,),
            daemon=True,
            ).start()

    @scpi(r":INSTRument:CHANNEL(.*):REAd\?")
    def _read_voltage_meas(self, channel: int) -> float:
        return self._voltage[channel]


class MockerResponse(Enum):
    PASS_COMMAND = auto()
    FAIL_COMMAND = auto()
    UPPER_COMMAND = auto()
    LOWER_COMMAND = auto()
    OKAY_BOARDER = auto()
    NOT_OKAY_BOARDER = auto()


class Mocker6(BaseMocker):
    """
    A mocker class with mixed scpi and scpi_raw_regex commands.
    """

    def __init__(self, call_delay: float = 0.0) -> None:
        super().__init__(call_delay=call_delay)

    # This command can pass if the command sent to device doesn't overlap with below.
    @scpi(r":PASSfail")
    def _pass_command_scpi(self) -> int:
        return MockerResponse.PASS_COMMAND.value

    # This command should always fail because of overlap with above
    @scpi_raw_regex(r":passFAIL")
    def _fail_command_scpi_raw(self) -> int:
        # We shouldn't be able to get this return value back
        return MockerResponse.FAIL_COMMAND.value

    # This command should always fail because of overlap with above
    @scpi_raw_regex(r":CASETEST")
    def _case_test_upper(self) -> int:
        return MockerResponse.UPPER_COMMAND.value

    @scpi_raw_regex(r":casetest")
    def _case_test_lower(self) -> int:
        return MockerResponse.LOWER_COMMAND.value

    @scpi_raw_regex(r"okay->")
    def _okay_boarder_test(self) -> int:
        return MockerResponse.OKAY_BOARDER.value

    @scpi_raw_regex(r"<-not okay->$")
    def _not_okay_boarder(self) -> int:
        return MockerResponse.NOT_OKAY_BOARDER.value


resources = {
    "MOCK0::mock1::INSTR": Mocker1(),
    "MOCK0::mock2::INSTR": Mocker2(),
    "MOCK0::mock3::INSTR": Mocker3(),
    "MOCK0::mock4::INSTR": Mocker4(),
    "MOCK0::mock5::INSTR": Mocker5(),
    "MOCK0::mock6::INSTR": Mocker6(),
}
