from typing import Dict

from pyvisa_mock.base.base_mocker import BaseMocker

resources: Dict[str, BaseMocker] = {}


def register_resource(address: str, mocker: BaseMocker) -> None:
    resources[address] = mocker


def register_resources(new_resources: Dict[str, BaseMocker]) -> None:
    resources.update(new_resources)
