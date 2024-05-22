from collections import defaultdict
from pyvisa import ResourceManager
from pyvisa_mock.base.base_mocker import BaseMocker, scpi
from pyvisa_mock.base.register import register_resource


class MockerChannel(BaseMocker):
    """
    A mocker channel for a multi channel voltage source.
    Voltages are zero by default
    """

    def __init__(self, call_delay: float = 0.0):
        super().__init__(call_delay=call_delay)
        self._voltage = 0

    # Lets define handler functions.

    @scpi(":VOLTage <voltage>")
    def _set_voltage(self, voltage: float) -> None:
        self._voltage = voltage

    @scpi(":VOLTage?")
    def _get_voltage(self) -> float:
        return self._voltage


class Mocker(BaseMocker):
    """
    The main mocker class.
    """

    def __init__(self, call_delay: float = 0.0):
        super().__init__(call_delay=call_delay)
        self._channels = defaultdict(MockerChannel)

    @scpi("*IDN?")
    def idn(self) -> str:
        """
        'vendor', 'model', 'serial', 'firmware'
        """
        return "Mocker,testing,00000,0.01"

    @scpi(":INSTRument:CHAnnel<channel>")
    def _get_channel(self, channel: int) -> MockerChannel:
        return self._channels[channel]


register_resource("MOCK0::mock1::INSTR", Mocker())

rc = ResourceManager(visa_library="@mock")
res = rc.open_resource("MOCK0::mock1::INSTR")
res.write(":INSTR:CHANNEL1:VOLT 2.3")
reply = res.query(":INSTR:CHA1:VOLT?")  # This should return '2.3'
print(reply)
reply = res.query(
    ":instrument:channel1:voltage?"
)  # We can either use the short form or the long form
print(reply)
