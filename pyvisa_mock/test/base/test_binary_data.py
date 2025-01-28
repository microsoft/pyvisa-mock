from pyvisa import Resource, ResourceManager
from pyvisa.resources import MessageBasedResource
from pyvisa.util import to_ieee_block

from pyvisa_mock.base.register import register_resources
from pyvisa_mock.test.mock_instruments import instruments


def test_read_bytes_from_bytes_response():
    register_resources(instruments.resources)

    rc = ResourceManager(visa_library="@mock")
    resource: MessageBasedResource|Resource = rc.open_resource("MOCK0::mock7::INSTR")
    resource.write("FETCh?")

    data = resource.read_bytes(1)
    assert data == b"1"

    data = resource.read_bytes(10)
    assert data == b".0,2.0,3.0"


def test_read_bytes_from_bytearray_response(monkeypatch):
    monkeypatch.setattr(instruments.Mocker7, "FETCH_DATA", bytearray(b"4.0,5.0,6.0"))

    register_resources(instruments.resources)

    rc = ResourceManager(visa_library="@mock")
    resource: MessageBasedResource|Resource = rc.open_resource("MOCK0::mock7::INSTR")
    resource.write("FETCh?")

    data = resource.read_bytes(1)
    assert data == b"4"

    data = resource.read_bytes(10)
    assert data == b".0,5.0,6.0"

def test_query_binary_values(monkeypatch):
    data = to_ieee_block([1.0, 2.0, 3.0])
    monkeypatch.setattr(instruments.Mocker7, "FETCH_DATA", data)

    register_resources(instruments.resources)
    rc = ResourceManager(visa_library="@mock")
    resource: MessageBasedResource|Resource = rc.open_resource("MOCK0::mock7::INSTR")

    data = resource.query_binary_values("FETCh?")
    assert data == [1.0, 2.0, 3.0]


def test_read_binary_values(monkeypatch):
    data = to_ieee_block([1.0, 2.0, 3.0])
    monkeypatch.setattr(instruments.Mocker7, "FETCH_DATA", data)

    register_resources(instruments.resources)
    rc = ResourceManager(visa_library="@mock")
    resource: MessageBasedResource|Resource = rc.open_resource("MOCK0::mock7::INSTR")
    resource.write("FETCh?")

    data = resource.read_binary_values()
    assert data == [1.0, 2.0, 3.0]
