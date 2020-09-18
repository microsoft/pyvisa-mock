import visa_mock as pyvisa_mock
import time

from pyvisa import ResourceManager
from pyvisa.errors import VisaIOError
from pyvisa.constants import StatusCode

from visa_mock.base.register import register_resource

from geiger_counter_mock import GeigerCounterMock, MessageCode

gc_address = 'MOCK0::mock1::INSTR'
register_resource(gc_address, GeigerCounterMock())

rm = ResourceManager('@mock')
rm.list_resources()
inst = rm.open_resource(gc_address)
print(inst.query('*IDN?'))

inst.write('ALERT:EXPOSURE:THRESHOLD 8.01')
print(inst.query('ALERT:EXPOSURE:THRESHOLD?'))
inst.write('ALERT:READING:THRESHOLD 0.10')


try:
    inst.write('MEAS:START')

    print('waiting for exposure limit')
    for i in range(100):
        try:
            inst.wait_for_srq(timeout=100)
        except VisaIOError as e:
            if e.error_code == StatusCode.error_timeout:
                pass
            else:
                raise e
        else:
            stb = inst.stb
            print(f'read stb is {hex(stb)}')
            if stb & MessageCode.READING_LIMIT_EXCEEDED.value:
                print('reading threshold reached')
            if stb & MessageCode.EXPOSURE_LIMIT_EXCEEDED.value:
                print(f'exposure threshold reached {inst.query("MEAS:EXPOSURE?")}')
                inst.write('MEAS:EXPOSURE:RESET')
            # Clear the status byte register
            inst.write('*CLS')

finally:
    inst.write('MEAS:STOP')
    print('done')
