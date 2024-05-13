from pyvisa_mock.base.register import register_resources
from pyvisa_mock.test.mock_instruments import instruments

from pyvisa import ResourceManager


def test_sanity():

    register_resources(instruments.resources)

    rc = ResourceManager(visa_library="@mock")
    res = rc.open_resource("MOCK0::mock1::INSTR")
    res.write(":INSTR:CHANNEL1:VOLT 2.3")
    reply = res.query(":INSTR:CHANNEL1:VOLT?")

    assert reply == '2.3'
