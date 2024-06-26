import pytest
import time
from pyvisa_mock.base.base_mocker import BaseMocker
from pyvisa_mock.test.mock_instruments.instruments import Mocker1


def time_command(mocker: BaseMocker, command: str) -> float:
    start = time.time()
    mocker.send(command)
    return time.time() - start


def test_delay_on_instrument():
    call_delay = 1.0        # unit: [sec]
    mocker = Mocker1()

    # By default, there is no delay:
    time_w_no_delay = time_command(mocker, ":INSTR:CHANNEL1:VOLT?")
    # To introduce the delay to the whole instrument:
    mocker.set_call_delay(call_delay)
    time_w_delay = time_command(mocker, ":INSTR:CHANNEL1:VOLT?")
    assert time_w_delay - time_w_no_delay == pytest.approx(call_delay, 0.1)


def test_delay_on_command():
    call_delay = 2.0        # unit: [sec]
    mocker = Mocker1()
    cmd_w_delay = ":INSTRument:CHANNEL<channel>:VOLTage <value>"

    # To introduce delay to one cmd only:
    mocker.set_call_delay(call_delay, cmd_w_delay)
    time_w_delay = time_command(mocker, ":INSTR:CHANNEL1:VOLT 12")
    # Other comands should have no delay:
    time_w_no_delay = time_command(mocker, ":INSTR:CHANNEL1:VOLT?")
    assert time_w_delay - time_w_no_delay == pytest.approx(call_delay, 0.1)
