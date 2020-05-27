import pytest
from visa_mock.test.mock_instruments.instruments import Mocker0, Mocker1, Mocker2, Mocker3, Mocker4


def test_base_long_and_short_form_match():
    """
    In Mocker0, "INSTRument" is the long form, and "INSTR" is the short form.
    They are also NOT case-sensitive. Same for the keyword "VOLTage".

    The user can use either the long form or the short form, but not partial.

    The user should also use only the long form or the short form, but not mixed of the two.
    """
    mocker = Mocker0()
    mocker.send(":instr:channel1:volt 12")
    mocker.send(":Instrument:channel2:voltage 13.4")

    voltage = mocker.send(":inStrument:channel1:vOlTage?")
    assert voltage == "12.0"

    voltage = mocker.send(":iNstR:channel2:volt?")
    assert voltage == "13.4"

    with pytest.raises(ValueError, match='Unknown SCPI command'):
        voltage = mocker.send(":instru:channel2:volt?")


def test_base():
    mocker = Mocker1()
    mocker.send(":INSTR:CHANNEL1:VOLT 12")
    mocker.send(":INSTR:CHANNEL2:VOLT 13.4")

    voltage = mocker.send(":INSTR:CHANNEL1:VOLT?")
    assert voltage == "12.0"

    voltage = mocker.send(":INSTR:CHANNEL2:VOLT?")
    assert voltage == "13.4"


def test_two_of_same_kind():

    mocker1 = Mocker1()
    mocker2 = Mocker1()

    mocker1.send(":INSTR:CHANNEL1:VOLT 12")
    voltage = mocker1.send(":INSTR:CHANNEL1:VOLT?")
    assert voltage == "12.0"

    mocker2.send(":INSTR:CHANNEL1:VOLT 13.4")
    voltage = mocker2.send(":INSTR:CHANNEL1:VOLT?")
    assert voltage == "13.4"


def test_one_of_each_kind():
    mocker1 = Mocker1()
    mocker2 = Mocker2()

    mocker1.send(":INSTR:CHANNEL1:VOLT 12")
    voltage = mocker1.send(":INSTR:CHANNEL1:VOLT?")
    assert voltage == "12.0"

    mocker2.send(":INSTR:CHANNEL1:VOLT 13.4")
    voltage = mocker2.send(":INSTR:CHANNEL1:VOLT?")
    assert voltage == "26.8"


def test_modular_mock():

    mocker3 = Mocker3()
    mocker3.send(":CHANNEL1:VOLT 12")
    voltage = mocker3.send(":CHANNEL1:VOLT?")
    assert voltage == "12.0"

    mocker3.send(":CHANNEL2:VOLT 13.4")
    voltage = mocker3.send(":CHANNEL2:VOLT?")
    assert voltage == "13.4"


def test_modular_2_mock():

    mocker4 = Mocker4()

    voltage = mocker4.send(":INSTR1:CHANNEL1:VOLT?")
    assert voltage == "0"
    mocker4.send(":INSTR1:CHANNEL1:VOLT 12")
    voltage = mocker4.send(":INSTR1:CHANNEL1:VOLT?")
    assert voltage == "12.0"

    voltage = mocker4.send(":INSTR1:CHANNEL2:VOLT?")
    assert voltage == "0"
    mocker4.send(":INSTR1:CHANNEL2:VOLT 13.4")
    voltage = mocker4.send(":INSTR1:CHANNEL2:VOLT?")
    assert voltage == "13.4"

    voltage = mocker4.send(":INSTR2:CHANNEL1:VOLT?")
    assert voltage == "0"
    mocker4.send(":INSTR2:CHANNEL1:VOLT -12")
    voltage = mocker4.send(":INSTR2:CHANNEL1:VOLT?")
    assert voltage == "-12.0"

    voltage = mocker4.send(":INSTR2:CHANNEL2:VOLT?")
    assert voltage == "0"
    mocker4.send(":INSTR2:CHANNEL2:VOLT -13.4")
    voltage = mocker4.send(":INSTR2:CHANNEL2:VOLT?")
    assert voltage == "-13.4"
