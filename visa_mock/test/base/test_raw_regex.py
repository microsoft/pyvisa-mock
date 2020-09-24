import pytest
from visa_mock.test.mock_instruments.instruments import (
    Mocker6,
    MockerResponse,
    MockerChannel,
    )
from visa_mock.base.base_mocker import MockingError, scpi_raw_regex, BaseMocker


def test_raw_regex_overlap():
    """
    """
    mocker = Mocker6()
    # These should all match the pass command
    assert int(mocker.send(":PASSfail")) == MockerResponse.PASS_COMMAND.value
    assert int(mocker.send(":PASS")) == MockerResponse.PASS_COMMAND.value
    assert int(mocker.send(":pass")) == MockerResponse.PASS_COMMAND.value
    assert int(mocker.send(":passfail")) == MockerResponse.PASS_COMMAND.value

    # This should match the pass and fail command, and fail with multiple matches
    with pytest.raises(MockingError):
        mocker.send(":passFAIL")

    # This shouldn't match any test
    with pytest.raises(ValueError):
        mocker.send(":CaSeTeSt")
    # This should match the case tests
    assert int(mocker.send(":CASETESTjunk")) == MockerResponse.UPPER_COMMAND.value
    assert int(mocker.send(":casetest")) == MockerResponse.LOWER_COMMAND.value

    assert int(mocker.send("okay->")) == MockerResponse.OKAY_BOARDER.value
    assert int(mocker.send("okay->a")) == MockerResponse.OKAY_BOARDER.value
    with pytest.raises(ValueError):
        mocker.send("aokay->")

    assert int(mocker.send("<-not okay->")) == MockerResponse.NOT_OKAY_BOARDER.value

    with pytest.raises(ValueError):
        mocker.send("a<-not okay->")
    with pytest.raises(ValueError):
        mocker.send("<-not okay->a")

    with pytest.raises(MockingError):
        class ShouldFail(BaseMocker):
            @scpi_raw_regex('fake_stuff')
            def should_fail(self) -> MockerChannel:
                pass


