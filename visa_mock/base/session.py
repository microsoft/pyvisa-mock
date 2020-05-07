"""
Large parts of this code has been copied directly from pyvisa-sim

https://github.com/pyvisa/pyvisa-sim
"""
from typing import Optional
from pyvisa import constants, attributes, rname
import logging

from visa_mock.base.base_mocker import BaseMocker


logger = logging.getLogger()


class Session:

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

    @property
    def device(self) -> BaseMocker:
        return self._device

    @device.setter
    def device(self, dev: BaseMocker) -> None:
        self._device = dev

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
