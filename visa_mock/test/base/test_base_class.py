from visa_mock.test.mock_instruments.instruments import Mocker0, Mocker1, Mocker2, Mocker3, Mocker4


def test_base_partial_match():
    """
    In Mocker0, "INSTRument" is used, but only the "INSTR" part is required. It's also NOT case-sensitive.
    """
    mocker = Mocker0()
    mocker.send(":instr:channel1:volt 12")
    mocker.send(":instr:channel2:volt 13.4")

    voltage = mocker.send(":instr:channel1:volt?")
    assert voltage == "12.0"

    voltage = mocker.send(":instr:channel2:volt?")
    assert voltage == "13.4"


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
