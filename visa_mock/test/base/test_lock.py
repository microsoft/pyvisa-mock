from pyvisa import ResourceManager, Resource
from threading import Thread, Event
from pytest import raises

from visa_mock.base.register import register_resources
from visa_mock.test.mock_instruments import instruments
from pyvisa.constants import StatusCode
from pyvisa.errors import VisaIOError


def test_lock_context():

    register_resources(instruments.resources)

    rc = ResourceManager(visa_library="@mock")
    res: Resource = rc.open_resource("MOCK0::mock1::INSTR")

    res.write(":INSTR:CHANNEL1:VOLT 2.3")
    with res.lock_context():
        reply = res.query(":INSTR:CHANNEL1:VOLT?")
        assert reply == '2.3'

def test_lock_timeout():

    register_resources(instruments.resources)

    rc = ResourceManager(visa_library="@mock")
    res: Resource = rc.open_resource("MOCK0::mock1::INSTR")
    res.write(":INSTR:CHANNEL1:VOLT 2.3")

    res.write(":INSTR:CHANNEL1:VOLT 2.3")

    def blocking_thread(res: Resource, event: Event):
        with res.lock_context():
            event.wait()

    block_release: Event = Event()
    blocker: Thread = Thread(
        target=blocking_thread,
        args=[res, block_release],
        )
    try:
        blocker.start()

        with raises(VisaIOError) as e:
            with res.lock_context(timeout=0):
                res.query(":INSTR:CHANNEL1:VOLT?")
        assert e.value.error_code == StatusCode.error_timeout
    finally:
        block_release.set()
        blocker.join()
    reply = res.query(":INSTR:CHANNEL1:VOLT?")
    assert reply == '2.3'


def test_lock():
    register_resources(instruments.resources)

    rc = ResourceManager(visa_library="@mock")
    res: Resource = rc.open_resource("MOCK0::mock1::INSTR")
    res.lock_excl(timeout=0)
    res.unlock()
