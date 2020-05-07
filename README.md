# pyvisa_mock

pyvisa-mock aims to provide similar functionality as [pyvisa-sim](https://pyvisa-sim.readthedocs.io/en/latest/), however, instead of a static YAML file providing query/response items, a dynamic python object is responsible for handling queries. 

## Example

```python
from collections import defaultdict
from visa import ResourceManager
from visa_mock.base.base_mocker import BaseMocker, scpi
from visa_mock.base.register import register_resource

class MockerChannel(BaseMocker): 
    """
    A mocker channel for a multi channel voltage source. 
    Voltages are zero by default
    """
    
    def __init__(self, call_delay: float = 0.0):
        super().__init__(call_delay=call_delay)
        self._voltage = 0
    
    # Lets define handler functions. Notice how we can be 
    # lazy in our regular expressions (using ".*"). The 
    # typehints will be used to cast strings to the 
    # required types
    
    @scpi(r":VOLT (.*)") 
    def _set_voltage(self, value: float) -> None:
        self._voltage = value
    
    @scpi(r":VOLT\?")
    def _get_voltage(self) -> float: 
        return self._voltage


class Mocker(BaseMocker):
    """
    The main mocker class. 
    """

    def __init__(self, call_delay: float = 0.0):
        super().__init__(call_delay=call_delay)
        self._channels = defaultdict(MockerChannel)

    @scpi("\*IDN\?")
    def idn(self) -> str: 
        """
        'vendor', 'model', 'serial', 'firmware'
        """
        return "Mocker,testing,00000,0.01"
    
    @scpi(r":INSTR:CHANNEL(.*)")
    def _get_channel(self, channel: int) -> MockerChannel:
        return self._channels[channel] 
        
register_resource("MOCK0::mock1::INSTR", Mocker())

rc = ResourceManager(visa_library="@mock")
res = rc.open_resource("MOCK0::mock1::INSTR")
res.write(":INSTR:CHANNEL1:VOLT 2.3")
reply = res.query(":INSTR:CHANNEL1:VOLT?")  # This should return '2.3'
```
