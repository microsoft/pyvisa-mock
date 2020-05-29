from collections import defaultdict
from visa_mock.base.base_mocker import BaseMocker, scpi


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


resources = {
    "MOCK0::mock1::INSTR": Mocker1(),
    "MOCK0::mock2::INSTR": Mocker2(),
    "MOCK0::mock3::INSTR": Mocker3(),
    "MOCK0::mock4::INSTR": Mocker4(),
}
