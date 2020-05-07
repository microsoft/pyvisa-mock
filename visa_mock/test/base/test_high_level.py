from visa_mock.base.register import register_resources
from visa_mock.test.mock_instruments import instruments

from visa import ResourceManager


def test_sanity():

    register_resources(instruments.resources)

    rc = ResourceManager(visa_library="@mock")
    res = rc.open_resource("MOCK0::mock1::INSTR")
    res.write(":INSTR:CHANNEL1:VOLT 2.3")
    reply = res.query(":INSTR:CHANNEL1:VOLT?")

    assert reply == '2.3'
