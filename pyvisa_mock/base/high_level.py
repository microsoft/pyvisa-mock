from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
from time import perf_counter
from typing_extensions import ClassVar
from datetime import timedelta

from pyvisa import constants, highlevel, rname, errors
from pyvisa.constants import (
    InterfaceType,
    StatusCode,
    EventType,
    EventMechanism,
    )
from pyvisa.resources.resource import Resource
from pyvisa.resources import SerialInstrument
from pyvisa.rname import register_subclass, ResourceName
from pyvisa.typing import VISASession

from pyvisa_mock.base.register import resources
from pyvisa_mock.base.session import (
        Session,
        EventNotEnabledError,
        EventNotDisabledError,
        EventTimeoutError,
        EventNotSupportedError,
        )

STATUS_CODE = int


@register_subclass
@dataclass
class MockInstr(ResourceName):
    """
    for mock instrument, the syntax is:
    MOCK[board]::[name]::INSTR
    """
    board: str = "0"
    name: str = "mock"

    interface_type: ClassVar[str] = "MOCK"
    resource_class: ClassVar[str] = "INSTR"
    is_rc_optional: ClassVar[bool] = False


mock_instr = MockInstr()

mock_constant = 1000
InterfaceType.mock = mock_constant


@Resource.register(mock_constant, "INSTR")
class MockResource(SerialInstrument):

    def read(self, **kwargs) -> str:
        reply, status_code = self.visalib.read(self.session)
        return reply

    def write(self, message: str, **kwargs) -> Tuple[int, STATUS_CODE]:
        self.visalib.write(self.session, message)
        return len(message), StatusCode.success

    def query(self, message: str, **kwargs) -> str:
        self.write(message)
        return self.read()

    @property
    def stb(self) -> int:
        """Service request status register."""
        return self.read_stb()

    def read_stb(self) -> int:
        """Service request status register."""
        value, _ = self.visalib.read_stb(self.session)
        return value

    def wait_for_srq(self, timeout: int = 25000) -> None:
        """Wait for a serial request (SRQ) coming from the instrument.

        Note that this method is not ended when *another* instrument signals an
        SRQ, only *this* instrument.

        Parameters
        ----------
        timeout : int
            Maximum waiting time in milliseconds. Defaul: 25000 (milliseconds).
            None means waiting forever if necessary.

        (NOTE: This method is copied from the pyvisa library)
        """
        self.enable_event(
            EventType.service_request, EventMechanism.queue
        )

        if timeout and not 0 <= timeout <= 4294967295:
            raise ValueError("timeout value is invalid")

        starting_time = perf_counter()

        while True:
            if timeout is None:
                adjusted_timeout = constants.VI_TMO_INFINITE
            else:
                adjusted_timeout = int(
                    (starting_time + timeout / 1e3 - perf_counter()) * 1e3
                )
                if adjusted_timeout < 0:
                    adjusted_timeout = 0

            self.wait_on_event(EventType.service_request, adjusted_timeout)
            if self.stb & 0x40:
                break

        self.discard_events(
            EventType.service_request, EventMechanism.queue
        )


class MockVisaLibrary(highlevel.VisaLibraryBase):

    def _init(self) -> None:

        self._sessions: Dict[int, Session] = {}

    def list_resources(self, session: int, query='?*::INSTR') -> List[str]:

        resources_list = rname.filter(list(resources), query)

        if resources_list:
            return resources_list

        raise errors.VisaIOError(
            errors.StatusCode.error_resource_not_found.value
        )

    def new_session(self, session: Session = None) -> int:

        if self._sessions:
            new_session_idx = max(self._sessions) + 1
        else:
            new_session_idx = 1

        if session is None:
            session = Session(new_session_idx, "MOCK0::name::INSTR")

        session.session_index = new_session_idx
        self._sessions[session.session_index] = session
        return new_session_idx

    def open_default_resource_manager(self) -> Tuple[int, STATUS_CODE]:

        new_session_idx = self.new_session()
        return new_session_idx, StatusCode.success

    def open(
            self,
            manager_session_idx: int,
            resource_name: str,
            access_mode=constants.AccessModes.no_lock,
            open_timeout=constants.VI_TMO_IMMEDIATE
    ) -> Tuple[int, STATUS_CODE]:

        if resource_name not in resources:
            raise ValueError(f"Unknown resource {resource_name}")

        device = resources[resource_name]
        session = Session(manager_session_idx, resource_name)
        session.device = device
        new_session_index = self.new_session(session)
        return new_session_index, StatusCode.success

    def close(self, session_idx: int) -> STATUS_CODE:
        if session_idx not in self._sessions:
            return StatusCode.error_invalid_object

        del self._sessions[session_idx]
        return StatusCode.success

    def get_attribute(self, session_idx: int, attribute: int) -> Tuple[Any, STATUS_CODE]:
        """
        """
        return self._sessions[session_idx].get_attribute(attribute)

    def set_attribute(self, session_idx: int, attribute: int, attribute_state: Any) -> STATUS_CODE:
        """
        """
        return self._sessions[session_idx].set_attribute(attribute, attribute_state)

    def disable_event(
        self,
        session: int,
        event_type: EventType,
        mechanism: EventMechanism,
    ) -> StatusCode:
        """Disable notification for an event type(s) via the specified mechanism(s).

        Corresponds to viDisableEvent function of the VISA library.

        Parameters
        ----------
        session : int
            Unique logical identifier to a session.
        event_type : EventType
            Event type.
        mechanism : EventMechanism
            Event handling mechanisms to be disabled.

        Returns
        -------
        StatusCode
            Return value of the library call.

        """
        try:
            cur_session = self._sessions[session]
        except KeyError as e:
            raise errors.VisaIOError(StatusCode.error_connection_lost) from e
        if mechanism != EventMechanism.queue:
            return StatusCode.success
        try:
            cur_session.disable_event(event_type=event_type)
        except (EventNotEnabledError, EventNotSupportedError):
            # Okay to re-disable an event or disable unsupported event
            pass
        return StatusCode.success

    def discard_events(
        self,
        session: int,
        event_type: EventType,
        mechanism: EventMechanism,
    ) -> StatusCode:
        """Discard event occurrences for a given type and mechanisms in a session.

        Corresponds to viDiscardEvents function of the VISA library.

        Parameters
        ----------
        session : int
            Unique logical identifier to a session.
        event_type : constans.EventType
            Logical event identifier.
        mechanism : EventMechanism
            Specifies event handling mechanisms to be discarded.

        Returns
        -------
        StatusCode
            Return value of the library call.

        """
        try:
            cur_session = self._sessions[session]
        except KeyError as e:
            raise errors.VisaIOError(StatusCode.error_connection_lost) from e
        if mechanism != EventMechanism.queue:
            return StatusCode.success
        try:
            cur_session.discard_events(event_type=event_type)
        except (EventNotEnabledError, EventNotSupportedError) as e:
            raise errors.VisaIOError(StatusCode.error_invalid_event) from e
        return StatusCode.success

    def enable_event(
        self,
        session: int,
        event_type: EventType,
        mechanism: EventMechanism,
        context: None = None,
    ) -> StatusCode:
        """Enable event occurrences for specified event types and mechanisms in a session.

        Corresponds to viEnableEvent function of the VISA library.

        Parameters
        ----------
        session : VISASession
            Unique logical identifier to a session.
        event_type : EventType
            Logical event identifier.
        mechanism : EventMechanism
            Specifies event handling mechanisms to be enabled.
        context : None, optional
            Unused parameter...

        Returns
        -------
        StatusCode
            Return value of the library call.

        """
        try:
            cur_session = self._sessions[session]
        except KeyError as e:
            raise errors.VisaIOError(StatusCode.error_connection_lost) from e
        if mechanism != EventMechanism.queue:
            raise errors.VisaIOError(StatusCode.error_invalid_mechanism)
        try:
            cur_session.enable_event(event_type)
        except EventNotSupportedError as e:
            raise errors.VisaIOError(StatusCode.error_invalid_event) from e
        except EventNotDisabledError:
            # Okay to re-enable event
            pass
        return StatusCode.success

    def wait_on_event(
        self,
        session: int,
        in_event_type: EventType,
        timeout: int
    ) -> Tuple[EventType, int, StatusCode]:
        """Wait for an occurrence of the specified event for a given session.

        Corresponds to viWaitOnEvent function of the VISA library.

        Parameters
        ----------
        session : VISASession
            Unique logical identifier to a session.
        in_event_type : EventType
            Logical identifier of the event(s) to wait for.
        timeout : int
            Absolute time period in time units that the resource shall wait for
            a specified event to occur before returning the time elapsed error.
            The time unit is in milliseconds.

        Returns
        -------
        EventType
            Logical identifier of the event actually received
        int
            A handle specifying the unique occurrence of an event
        StatusCode
            Return value of the library call.

        """
        try:
            cur_session = self._sessions[session]
        except KeyError as e:
            raise errors.VisaIOError(StatusCode.error_connection_lost) from e
        timeout_td = timedelta(milliseconds=timeout)
        try:
            cur_session.wait_for_event(event_type=in_event_type, timeout=timeout_td)
        except (EventNotEnabledError, EventNotSupportedError) as e:
            raise errors.VisaIOError(StatusCode.error_invalid_event) from e
        except EventTimeoutError as e:
            raise errors.VisaIOError(StatusCode.error_timeout) from e
        return(in_event_type, 0, StatusCode.success)

    def read_stb(self, session: int) -> Tuple[int, StatusCode]:
        """Reads a status byte of the service request.

        Corresponds to viReadSTB function of the VISA library.

        Parameters
        ----------
        session : VISASession
            Unique logical identifier to a session.

        Returns
        -------
        int
            Service request status byte
        StatusCode
            Return value of the library call.

        """
        stb_val = self._sessions[session].stb
        return (stb_val, StatusCode.success)

    def read(self, session_idx: int, count: int = None) -> Tuple[str, STATUS_CODE]:
        reply = self._sessions[session_idx].read(count)
        return reply, StatusCode.success

    def write(self, session_idx: int, data: str) -> STATUS_CODE:
        self._sessions[session_idx].write(data)
        return StatusCode.success

    def clear(self, session_idx: int) -> None:
        return None

    @staticmethod
    def get_library_paths():
        """Override this method to return an iterable of possible library_paths
        to try in case that no argument is given.
        """
        return 'unset',

    def flush(
        self, session: VISASession, mask: constants.BufferOperation
    ) -> None:
        return None

    def lock(
            self,
            session: int,
            lock_type: constants.Lock,
            timeout: int,
            requested_key: Optional[str] = None,) -> Tuple[str, StatusCode]:
        """Establishes an access mode to the specified resources.
        Corresponds to viLock function of the VISA library.
        Parameters
        ----------
        session : VISASession
            Unique logical identifier to a session.
        lock_type : constants.Lock
            Specifies the type of lock requested.
        timeout : int
            Absolute time period (in milliseconds) that a resource waits to get
            unlocked by the locking session before returning an error.
        requested_key : Optional[str], optional
            Requested locking key in the case of a shared lock. For an exclusive
            lock it should be None.
        Returns
        -------
        Optional[str]
            Key that can then be passed to other sessions to share the lock, or
            None for an exclusive lock.
        StatusCode
            Return value of the library call.
        """
        if lock_type != constants.Lock.exclusive:
            raise NotImplementedError(f'Only constant.Lock.exclusive supported.  ({lock_type})')
        if requested_key is not None:
            raise NotImplementedError(f'Requested key is not supported. ({requested_key})')
        try:
            cur_session = self._sessions[session]
        except KeyError as e:
            raise errors.VisaIOError(StatusCode.error_connection_lost) from e
        acquired = cur_session.resource_lock.acquire(timeout=timeout/1000)
        if not acquired:
            raise errors.VisaIOError(StatusCode.error_timeout)
        return ('', StatusCode.success)

    def unlock(self, session: int) -> StatusCode:
        """Relinquish a lock for the specified resource.
        Corresponds to viUnlock function of the VISA library.
        Parameters
        ----------
        session : VISASession
            Unique logical identifier to a session.
        Returns
        -------
        StatusCode
            Return value of the library call.
        """
        try:
            cur_session = self._sessions[session]
        except KeyError as e:
            raise errors.VisaIOError(StatusCode.error_connection_lost) from e
        cur_session.resource_lock.release()
        return StatusCode.success
