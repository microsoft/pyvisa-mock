import pytest
import time
from visa_mock.base.register import register_resources
from visa_mock.base.high_level import MockResource
from visa_mock.test.mock_instruments import instruments
from visa_mock.test.mock_instruments.instruments import Mocker5

from pyvisa import ResourceManager
from pyvisa.errors import VisaIOError
from pyvisa.constants import StatusCode


def test_blocking_read():
    """
    Make sure the the measurement takes a while to complete and
    that other operations are fast.
    """
    register_resources(instruments.resources)
    rc = ResourceManager(visa_library="@mock")
    res: MockResource = rc.open_resource("MOCK0::mock5::INSTR")
    meas_time = Mocker5.meas_time

    start_time = time.time()
    res.write(":instr:channel1:volt 12")
    end_time = time.time()
    elapsted = end_time - start_time
    assert elapsted < meas_time/2

    start_time = time.time()
    voltage = res.query(":inStrument:channel1:vOlT?")
    end_time = time.time()
    elapsted = end_time - start_time
    assert elapsted > meas_time/2
    assert voltage == "12.0"


def test_non_blocking_read():
    """
    Make sure the the non blocking read is fast.
    """
    register_resources(instruments.resources)
    rc = ResourceManager(visa_library="@mock")
    res: MockResource = rc.open_resource("MOCK0::mock5::INSTR")
    meas_time = Mocker5.meas_time

    start_time = time.time()
    res.write(":instr:channel1:volt 12")
    end_time = time.time()
    elapsted = end_time - start_time
    assert elapsted < meas_time/2

    # clear the STB reg
    voltage = res.write("*CLS")

    # kick off reading
    start_time = time.time()
    res.write(":inStrument:channel1:MEAS")
    end_time = time.time()
    elapsted = end_time - start_time
    assert elapsted < meas_time/2

    # Make sure time out happens
    with pytest.raises(VisaIOError) as e:
        res.wait_for_srq(0)
    assert e.value.error_code == StatusCode.error_timeout

    # Wait for event interrupt
    start_time = time.time()
    res.wait_for_srq()
    end_time = time.time()
    elapsted = end_time - start_time
    assert elapsted > meas_time/2

    start_time = time.time()
    voltage = res.query(":inStrument:channel1:REAd?")
    end_time = time.time()
    elapsted = end_time - start_time
    assert elapsted < meas_time/2
    assert voltage == "12.0"
