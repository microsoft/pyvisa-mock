from pyvisa_mock.base.session import Session


def test_session():
    Session(0, "TCPIP0::mock:INSTR")
