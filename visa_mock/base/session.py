"""
Large parts of this code has been copied directly from pyvisa-sim

https://github.com/pyvisa/pyvisa-sim
"""
from typing import Optional, Dict
import logging
from queue import Queue, Empty
from threading import RLock
from datetime import timedelta

from pyvisa import constants, attributes, rname
from visa_mock.base.base_mocker import BaseMocker, StbRegister


logger = logging.getLogger()


class SessionError(Exception):
    pass


class EventNotEnabledError(SessionError):
    pass


class EventNotDisabledError(SessionError):
    pass


class EventTimeoutError(SessionError):
    pass


class EventNotSupportedError(SessionError):
    pass


class Session:
    _events: Dict[constants.EventType, Queue]
    _events_enabled: Dict[constants.EventType, bool]
    # Serialized access to the dictionary not the events
    _events_dict_lock: RLock
    _SUPPORTED_EVENTS = [
        constants.EventType.service_request,
        ]
    _stb_register: StbRegister

    def __init__(
            self,
            resource_manager_session: int,
            resource_name: str,
            parsed: rname.ResourceName = None,
    ) -> None:

        if parsed is None:
            parsed = rname.parse_resource_name(resource_name)

        self.parsed = parsed

        self.attrs = {
            constants.VI_ATTR_RM_SESSION: resource_manager_session,
            constants.VI_ATTR_RSRC_NAME: str(parsed),
            constants.VI_ATTR_RSRC_CLASS: parsed.resource_class,
            constants.VI_ATTR_INTF_TYPE: parsed.interface_type_const
        }

        self.session_type = None
        self.session_index = resource_manager_session
        self._device: Optional[BaseMocker] = None
        self._read_buffer = ""
        self._events: Dict[constants.EventType, Queue] = {
            i: Queue()
            for i in self._SUPPORTED_EVENTS
            }
        self._events_enabled: Dict[constants.EventType, bool] = {
            constants.EventType.service_request: False
            for i in self._SUPPORTED_EVENTS
            }
        self._events_dict_lock = RLock()
        self._stb_register: StbRegister = StbRegister()

    @property
    def stb(self) -> int:
        rval = self._stb_register.value
        self._stb_register.value = 0
        return rval

    @stb.setter
    def stb(self, stb: int):
        self._stb_register.value = stb

    @property
    def device(self) -> BaseMocker:
        return self._device

    @device.setter
    def device(self, dev: BaseMocker) -> None:
        self._device = dev
        self._device.events = dict(self._events)
        self._device.stb_register = self._stb_register

    def get_attribute(self, attribute):  # TODO: type hints
        """
        """

        # Check that the attribute exists.
        if attribute not in attributes.AttributesByID:
            return 0, constants.StatusCode.error_nonsupported_attribute

        attr = attributes.AttributesByID[attribute]

        # Check that the attribute is valid for this session type.
        if not attr.in_resource(self.session_type):
            return 0, constants.StatusCode.error_nonsupported_attribute

        # Check that the attribute is readable.
        if not attr.read:
            raise Exception('Do not now how to handle write only attributes.')

        # Return the current value of the default according the VISA spec
        return self.attrs.setdefault(attribute, attr.default), constants.StatusCode.success

    def set_attribute(self, attribute, attribute_state):  # TODO: type hints
        """
        """

        # Check that the attribute exists.
        if attribute not in attributes.AttributesByID:
            return 0, constants.StatusCode.error_nonsupported_attribute

        attr = attributes.AttributesByID[attribute]

        # Check that the attribute is valid for this session type.
        if not attr.in_resource(self.session_type):
            return constants.StatusCode.error_nonsupported_attribute

        # Check that the attribute is writable.
        if not attr.write:
            return constants.StatusCode.error_attribute_read_only

        try:
            self.attrs[attribute] = attribute_state
        except ValueError:
            return constants.StatusCode.error_nonsupported_attribute_state

        return constants.StatusCode.success

    def write(self, message: str) -> None:
        reply = self.device.send(message)
        if reply is not None:
            self._read_buffer = reply

    def read(self) -> str:
        return self._read_buffer

    def ask(self, message: str):
        self.write(message)
        return self.read()

    """
    Event Logic:

    The following event methods enable sessions to support device events.

    Only queue type visa events are supported.  The event queues are stored in
    a dictionary.  Because of the reentrent/asyncronous nature of events, the
    dictionary access needs to be serialized.  The queues themselves already
    support threaded access.

    These methods are used by the visa mock library to implement mock of
    event.

    """
    def _clear_event_queue(self, event_type: constants.EventType) -> None:
        cur_event = self._events[event_type]
        with cur_event.mutex:
            cur_event.queue.clear()

    def enable_event(self, event_type: constants.EventType) -> None:
        if event_type not in self._SUPPORTED_EVENTS:
            raise EventNotSupportedError()
        with self._events_dict_lock:
            if not self._events_enabled[event_type]:
                self._clear_event_queue(event_type)
                self._events_enabled[event_type] = True
            else:
                raise EventNotDisabledError()

    def disable_event(self, event_type: constants.EventType) -> None:
        if event_type not in self._SUPPORTED_EVENTS:
            raise EventNotSupportedError()
        with self._events_dict_lock:
            if self._events_enabled[event_type]:
                self._events_enabled = False
            else:
                raise EventNotEnabledError('Event not enabled.')

    def discard_events(self, event_type: constants.EventType) -> None:
        if event_type not in self._SUPPORTED_EVENTS:
            raise EventNotSupportedError()
        with self._events_dict_lock:
            if not self._events_enabled:
                raise EventNotEnabledError('Event not enabled.')
            self._clear_event_queue(event_type)

    def set_event(self, event_type: constants.EventType) -> None:
        if event_type not in self._SUPPORTED_EVENTS:
            raise EventNotSupportedError()
        cur_event = self._events[event_type]
        if not self._events_enabled:
            raise EventNotEnabledError('Event not enabled.')
        cur_event.put(None)

    def wait_for_event(self, event_type: constants.EventType, timeout: timedelta) -> None:
        if event_type not in self._SUPPORTED_EVENTS:
            raise EventNotSupportedError()
        cur_event = self._events[event_type]
        if not self._events_enabled:
            raise EventNotEnabledError('Event not enabled.')
        try:
            cur_event.get(timeout=timeout.total_seconds())
        except Empty as e:
            raise EventTimeoutError() from e
