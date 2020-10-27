from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
from typing_extensions import ClassVar

from pyvisa import constants, highlevel, rname, errors
from pyvisa.constants import InterfaceType
from pyvisa.resources.resource import Resource
from pyvisa.resources import SerialInstrument
from pyvisa.rname import register_subclass, ResourceName
from pyvisa.typing import VISASession

from visa_mock.base.register import resources
from visa_mock.base.session import Session

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
        return len(message), constants.StatusCode.success

    def query(self, message: str, **kwargs) -> str:
        self.write(message)
        return self.read()


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
        return new_session_idx, constants.StatusCode.success

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
        return new_session_index, constants.StatusCode.success

    def close(self, session_idx: int) -> STATUS_CODE:
        if session_idx not in self._sessions:
            return constants.StatusCode.error_invalid_object

        del self._sessions[session_idx]
        return constants.StatusCode.success

    def disable_event(self, session_idx: int, event_type: int, mechanism: int) -> None:
        pass

    def discard_events(self, session_idx: int, event_type: int, mechanism: int) -> None:
        pass

    def get_attribute(self, session_idx: int, attribute: int) -> Tuple[Any, STATUS_CODE]:
        """
        """
        return self._sessions[session_idx].get_attribute(attribute)

    def set_attribute(self, session_idx: int, attribute: int, attribute_state: Any) -> STATUS_CODE:
        """
        """
        return self._sessions[session_idx].set_attribute(attribute, attribute_state)

    def read(self, session_idx: int, count: int = None) -> Tuple[str, STATUS_CODE]:
        reply = self._sessions[session_idx].read()
        return reply, constants.StatusCode.success

    def write(self, session_idx: int, data: str) -> STATUS_CODE:
        self._sessions[session_idx].write(data)
        return constants.StatusCode.success

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
