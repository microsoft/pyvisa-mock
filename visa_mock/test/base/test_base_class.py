import pytest
from visa_mock.test.mock_instruments.instruments import Mocker0, Mocker1, Mocker2, Mocker3, Mocker4


def test_base_long_and_short_form_match():
    """
    In Mocker0, "INSTRument" is the long form, and "INSTR" is the short form.
    They are also NOT case-sensitive. Same for the keyword "VOLTage".

    The user can use either the long form or the short form, but not partial.
    """
    mocker = Mocker0()
    mocker.send(":instr:channel1:volt 12")
    mocker.send(":Instrument:channel2:voltage 13.4")

    voltage = mocker.send(":inStrument:channel1:vOlT?")
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
    """
    Note: In the definition of the MockerChannel, which was called in Mocker3, keyword "VOLTage"
    was used. It means the user can use either the long form "voltage", or the short form "volt"
    in the scpi string. (both are case in-sensitive)
    """

    mocker3 = Mocker3()
    # to use long form "voltage":
    mocker3.send(":CHANNEL1:VOLTage 12")
    # short form "volt":
    voltage = mocker3.send(":CHANNEL1:VOLT?")
    assert voltage == "12.0"

    mocker3.send(":channel2:volt 13.4")
    voltage = mocker3.send(":channel2:voltage?")
    assert voltage == "13.4"


def test_modular_2_mock():
    """
    Note: In the definition of Mocker4, keyword "INSTRument" was used. As a result, the user can use
    either the long form "instrument" or the short form "instr", in addition to the "voltage"/"volt"
    situation described in the test_modular_mock() above.
    """

    mocker4 = Mocker4()

    voltage = mocker4.send(":INSTR1:CHANNEL1:VOLT?")
    assert voltage == "0"
    mocker4.send(":INSTR1:CHANNEL1:VOLT 12")
    voltage = mocker4.send(":INSTR1:CHANNEL1:VOLT?")
    assert voltage == "12.0"

    # to use long form "instrument" and "voltage", case in-sensitive:
    voltage = mocker4.send(":INSTRument1:CHANNEL2:VOLTage?")
    assert voltage == "0"
    mocker4.send(":INSTR1:CHANNEL2:VOLT 13.4")
    # to use long form "voltage" only
    voltage = mocker4.send(":INSTR1:CHANNEL2:VOLTage?")
    assert voltage == "13.4"

    # to use long form "instrument" only:
    voltage = mocker4.send(":instrument2:CHANNEL1:VOLT?")
    assert voltage == "0"
    mocker4.send(":INSTR2:CHANNEL1:VOLT -12")
    voltage = mocker4.send(":INSTR2:CHANNEL1:VOLT?")
    assert voltage == "-12.0"

    voltage = mocker4.send(":INSTR2:CHANNEL2:VOLT?")
    assert voltage == "0"
    mocker4.send(":INSTR2:CHANNEL2:VOLT -13.4")
    voltage = mocker4.send(":INSTR2:CHANNEL2:VOLT?")
    assert voltage == "-13.4"
