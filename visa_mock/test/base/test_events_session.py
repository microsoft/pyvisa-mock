import pytest
import logging
from unittest.mock import MagicMock
from datetime import timedelta
from visa_mock.base.session import (
    Session,
    EventNotEnabledError,
    EventNotDisabledError,
    EventNotSupportedError,
    EventTimeoutError,
    )
from visa_mock.base.high_level import MockResource
from visa_mock.test.mock_instruments import instruments
from visa_mock.test.mock_instruments.instruments import Mocker5

from pyvisa import ResourceManager
from pyvisa.errors import VisaIOError
from pyvisa.constants import StatusCode, EventType


@pytest.fixture
def session() -> Session:
    # Set supported events for testing
    Session._SUPPORTED_EVENTS = [
        EventType.service_request,
        EventType.pxi_interrupt,
        EventType.gpib_talk,
    ]
    return Session(
        resource_manager_session=0,
        resource_name='MOCK0::mock5::INSTR',
        )
    dev = Mocker5()
    session.device = dev


def test_session(session: Session):
    session.enable_event(EventType.service_request)
    session.set_event(EventType.service_request)
    session.wait_for_event(EventType.service_request, timeout=timedelta(0))
    session.set_event(EventType.service_request)
    assert(not session._events[EventType.service_request].empty())
    session.discard_events(EventType.service_request)
    assert(session._events[EventType.service_request].empty())
    session.disable_event(EventType.service_request)


def test_disable_disabled_session(session: Session):
    try:
        session.disable_event(EventType.service_request)
    except EventNotEnabledError:
        pass
    with pytest.raises(EventNotEnabledError):
        session.disable_event(EventType.service_request)


def test_enable_enabled_session(session: Session):
    try:
        session.enable_event(EventType.service_request)
    except EventNotDisabledError:
        pass
    with pytest.raises(EventNotDisabledError):
        session.enable_event(EventType.service_request)


def test_disable_event(session: Session):
    # Make sure event is disabled
    try:
        session.disable_event(EventType.service_request)
    except EventNotEnabledError:
        pass
    with pytest.raises(EventNotEnabledError):
        session.set_event(EventType.service_request)
    with pytest.raises(EventNotEnabledError):
        session.discard_events(EventType.service_request)
    with pytest.raises(EventNotEnabledError):
        session.disable_event(EventType.service_request)
    with pytest.raises(EventNotEnabledError):
        try:
            session.wait_for_event(EventType.service_request, timeout=timedelta(0))
        except EventTimeoutError:
            # If we do get here ignore exception so assert catches missed exception
            pass


def test_discard_event(session: Session):
    # Make sure event is enabled
    try:
        session.enable_event(EventType.service_request)
    except EventNotDisabledError:
        pass
    # Check that there are no events in queue
    with pytest.raises(EventTimeoutError):
        session.wait_for_event(EventType.service_request, timeout=timedelta(0))
    session.discard_events(EventType.service_request)
    # Check there there are no events in queue
    with pytest.raises(EventTimeoutError):
        session.wait_for_event(EventType.service_request, timeout=timedelta(0))
    session.set_event(EventType.service_request)
    # Check that there is an event to get
    session.wait_for_event(EventType.service_request, timeout=timedelta(0))
    # Check there there are no events in queue
    with pytest.raises(EventTimeoutError):
        session.wait_for_event(EventType.service_request, timeout=timedelta(0))


def test_multiple_events(session: Session):
    for cur_event in session._SUPPORTED_EVENTS:
        logging.getLogger().debug(session._events_enabled)
        try:
            session.enable_event(cur_event)
        except EventNotDisabledError:
            pass
    # Verify that all events enabled
    for cur_event in session._SUPPORTED_EVENTS:
        with pytest.raises(EventNotDisabledError):
            session.enable_event(cur_event)

    enabled_events = list(session._SUPPORTED_EVENTS)
    # Disable each event
    while enabled_events:
        cur_event = enabled_events.pop(0)
        session.disable_event(cur_event)
        # Make sure other events are still enabled
        for verify_enable_event in enabled_events:
            with pytest.raises(EventNotDisabledError):
                session.enable_event(verify_enable_event)


def test_unsupported_event_errors(session: Session):
    unsupported_event = EventType.tcpip_connect
    with pytest.raises(EventNotSupportedError):
        session.enable_event(unsupported_event)
    with pytest.raises(EventNotSupportedError):
        session.disable_event(unsupported_event)
    with pytest.raises(EventNotSupportedError):
        session.wait_for_event(unsupported_event, timeout=timedelta(0))
    with pytest.raises(EventNotSupportedError):
        session.set_event(unsupported_event)
    with pytest.raises(EventNotSupportedError):
        session.discard_events(unsupported_event)
