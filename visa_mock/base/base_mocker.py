from inspect import signature
from typing import (
    Dict, List, Callable,
    Any, cast, get_type_hints,
    Optional,
    )
from dataclasses import dataclass
import re
import time
from queue import Queue

from pyvisa import constants


@dataclass
class StbRegister():
    """
    This class is used to allow the mocker and session to both refrence one
    register instance.

    This is the most basic StbRegister with no extra logic around reading and
    writing the value.  Mockers can create custom StbRegister classes and
    override the _create_stb_register method.
    """
    value: int = 0


class MockingError(Exception):
    pass


class AnnotationError(Exception):
    pass


class SCPIHandler:
    """
    SCPI handlers contain *class* methods which are called at runtime when
    a SCPI message needs to be handled.

    The handler has two tasks:

    1) Because SCPI messages are strings, this handler will cast string
        values to the appropriate type depending on the annotation of the
        input method. The method will be called with the recast arguments.

    2) A handler can combine two handlers into one. Each handler handles part
        of a scpi string, for example ":INSTR:CHANNEL(.*)" and ":VOLTAGE?".
        The handler of the former returns a mock sub-module instance, containing
        a handler method for the latter substring.
    """
    @classmethod
    def from_method(cls, method: Callable) -> 'SCPIHandler':
        """
        Construct a handler from a class method.
        """
        parameters = dict(signature(method).parameters)

        try:
            parameters.pop("self")
        except KeyError:
            raise AnnotationError("This can only decorate class methods")

        type_hints = get_type_hints(method)

        try:
            return_type = type_hints.pop("return")
        except KeyError:
            raise AnnotationError("All functions must have an annotated return type")

        annotations = list(type_hints.values())

        if len(annotations) != len(parameters):
            raise AnnotationError(
                "This decorator requires all arguments to be annotated"
            )

        return cls(method, annotations, return_type)

    @classmethod
    def combine(
            cls,
            handler: 'SCPIHandler',
            sub_handler: 'SCPIHandler'
    ) -> 'SCPIHandler':
        """
        Combine two handlers, each processing part of a SCPI message.
        """
        handler_arg_count = len(handler.annotations)
        annotations = list(handler.annotations)
        annotations.extend(sub_handler.annotations)

        def method(self, *args):
            handler_args = args[:handler_arg_count]
            sub_handler_args = args[handler_arg_count:]
            # The first handler returns a submodule
            sub_module = handler(self, *handler_args)
            # 'sub_handler' is a *class* method, meaning that the
            # first argument needs to be a 'self'. This is
            # provided by the first handler.
            return sub_handler(
                sub_module,
                *sub_handler_args
            )

        return cls(
            method, annotations, sub_handler.return_type
        )

    def __init__(
            self,
            method: Callable,
            annotations: List,
            return_type: type
    ) -> None:
        """
        The __init__ is never called directly. We use 'from_method' and 'combine'
        instead

        Arguments:
            method: A method of a mocker class (not an instance method)
            annotations: A list of types acquired by inspecting the
                method type hints
            return_type: Specify the return type of the method.
        """
        self.method = method
        self.annotations = annotations
        self.return_type = return_type
        self.call_delay = None

    def __call__(self, mocker_self, *args):
        """
        The values in the arguments are strings because we have parsed a
        SCPI message string. Convert these string to the appropriate type
        using the annotations and call the handler method.
        """
        new_args = [
            annotation_type(value)
            for annotation_type, value in zip(self.annotations, args)
        ]

        return self.method(mocker_self, *new_args)


__tmp_scpi_dict__: Dict[str, SCPIHandler] = {}


class MockerMetaClass(type):
    """
    We need a custom metaclass as right after class declaration
    we need to modify class attributes: The `__scpi_dict__` needs
    to be populated
    """

    def __new__(cls, *args, **kwargs):
        mocker_class = super().__new__(cls, *args, **kwargs)
        mocker_class.__scpi_dict__ = dict(__tmp_scpi_dict__)

        names = list(__tmp_scpi_dict__.keys())
        for name in names:
            __tmp_scpi_dict__.pop(name)

        return mocker_class


class BaseMocker(metaclass=MockerMetaClass):
    __scpi_dict__: Dict[str, Callable] = {}
    _events: Dict[constants.EventType, Queue]
    # Should be created and set by session
    _stb_register: StbRegister

    def __init__(self, call_delay: float = 0.0):
        self._call_delay = call_delay
        # will be updated with supported events when registered with session
        self._events: Dict[constants.EventType, Queue] = {}
        self._stb_register: StbRegister = self._create_stb_register()

    def set_call_delay(
            self,
            call_delay: float,
            scpi_string: Optional[str] = None
    ) -> None:
        """
        This method set the call delay to either the whole instrument, or the
        scpi command specified.

        Args:
            call_delay: the intended delay value in second.
            scpi_string: when provided, this method will apply the call_delay
                to this scpi command only.
        """
        if scpi_string is None:
            self._call_delay = call_delay
        else:
            self.__scpi_dict__[compile_regular_expression(scpi_string)].call_delay = call_delay

    @classmethod
    def scpi(cls, scpi_string: str) -> Callable:
        def decorator(function):
            handler = SCPIHandler.from_method(function)
            return_type = handler.return_type

            regex = compile_regular_expression(scpi_string)

            if not isinstance(return_type, MockerMetaClass):
                __tmp_scpi_dict__[regex] = handler
                return

            # The function being decorated itself returns a Mocker. This is very
            # useful as it allows mockers to be modular. Further processing of the
            # scpi string will be handled by the submodule.
            # For an example, see instruments.py in the folder 'tests\mock_instruments\'
            # and specifically study the class 'Mocker3'

            SubModule = cast(MockerMetaClass, return_type)

            for regex_sub_string, sub_handler in SubModule.__scpi_dict__.items():
                __tmp_scpi_dict__[regex + regex_sub_string] = SCPIHandler.combine(
                    handler, sub_handler
                )

        return decorator

    def send(self, scpi_string: str) -> Any:

        found = False
        args = None
        handler = None

        for regex_pattern in self.__scpi_dict__:
            search_result = re.match(regex_pattern, scpi_string, re.IGNORECASE)
            if search_result:
                if not found:
                    found = True
                    handler = self.__scpi_dict__[regex_pattern]
                    args = search_result.groups()
                else:
                    raise MockingError(
                        f"SCPI command {scpi_string} matches multiple mocker "
                        f"class entries"
                    )

        if not found:
            raise ValueError(f"Unknown SCPI command {scpi_string}")

        if handler.call_delay is not None:
            time.sleep(handler.call_delay)
        else:
            time.sleep(self._call_delay)

        return str(handler(self, *args))

    """
    Event Support:

    The following methods enable event/inturrupt support.  Events are
    implemented with queues.  For each event type (consts.EventType) that is
    supported there is a corresponding queue.  These are stored in a
    dictionary.

    The session holds the state information about the device including events.
    When the mocker is registered with the session, the session sets the
    events dictionary in the mocker.
    """

    def set_events(self, events: Dict[constants.EventType, Queue]):
        """
        The event dict should be set by the session when the mocker is
        registered with the session.
        """
        self._events = events

    def get_events(self) -> Dict[constants.EventType, Queue]:
        return self._events

    events = property(
        fget=get_events,
        fset=set_events,
        doc="Events dictionary holds event queues.")

    def set_service_request_event(self):
        """
        Create an service request event.
        """
        try:
            cur_event = self.events[constants.EventType.service_request]
        except KeyError as e:
            raise MockingError(
                'Device does not support service request events or session not started.') from e
        cur_event.put(None)

    """
    Status Byte Support:

    The following methods enable status byte support.  The status byte register
    object is created by the mocker and shared with the session.  This allows
    the visa library mocker to access this register.  It also allows the
    mockers to implement custom logic.

    The session holds the state information about the device including the
    status byte.  When the mocker is registered with the session, the session
    gets the status byte reference from the mocker.

    """
    def _set_stb(self, stb: int) -> None:
        self.stb_register.value = stb

    def _get_stb(self) -> int:
        return self.stb_register.value

    stb = property(
        fget=_get_stb,
        fset=_set_stb,
        doc="stb register")

    @property
    def stb_register(self) -> StbRegister:
        return self._stb_register

    @staticmethod
    def _create_stb_register() -> StbRegister:
        """
        Allow the child class to override StbRegister creation with custom
        register with custom logic/behavior.
        """
        return StbRegister()


scpi = BaseMocker.scpi


def compile_regular_expression(scpi_string: str) -> str:
    """
    This function creates a regular expression pattern given a
    SCPI string. This regular expression follows the SCPI
    language rule where upper case letters denote the short form
    of a SCPI command. A SCPI message send by software to the
    instrument must match either the long or the short form.

    Examples:
        >>> scpi_pattern = "VOLTage:CHANnel(.*) (.*)"  # From an instrument manual
        >>> # the upper case part denotes the command short form
        >>> regex = compile_regular_expression(scpi_pattern)
        >>> # Sanity check to see if we match the long form:
        >>> assert re.match(regex, "voltage:channel1 2.3").groups() == ('1', '2.3')
        >>> # Check if we match the shortform:
        >>> assert re.match(regex, "volt:chan1 2.3").groups() == ('1', '2.3')
        >>> # We should be able to mix and match:
        >>> assert re.match(regex, "voltage:chan1 2.3").groups() == ('1', '2.3')

    Args:
        scpi_string: A string representing a pattern with which SCPI commands send by
            software should match. These patterns can often be found in instrument
            manuals.

    Returns:
        A regex pattern which will match long and short forms.

    Notes:
        This function works by finding all groups of lower case letters which are
        preceded by any upper case letter. These groups of lower case letters are
        marked as optional in the regex. Furthermore, this group is marked as
        non-capturing. Please see

        https://docs.python.org/3/howto/regex.html#non-capturing-and-named-groups

        Section "Non-capturing and Named Groups"
    """

    regex = re.sub(
        "(?P<chr>[A-Z])(?P<name>[a-z]+)", "\g<chr>(?:\g<name>)?",
        scpi_string
    )

    return regex
