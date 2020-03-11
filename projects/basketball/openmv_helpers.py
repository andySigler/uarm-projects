import json
import time

import serial
from serial.tools.list_ports import comports


OPENMV_SERIAL_DEFAULT_BAUDRATE = 115200
OPENMV_SERIAL_DEFAULT_TIMEOUT_SEC = 2
OPENMV_SERIAL_DEFAULT_RETRIES = 3
OPENMV_SERIAL_DEFAULT_MIN_DATA_LENGTH = 10


def find_camera_port():
    # TODO: smart way to discover OpenMV serial ports on OS
    return '/dev/tty.usbmodem0000000000111'


class OpenMV(serial.Serial):
    def __init__(self, *args, **kwargs):
        self._stay_open = kwargs.get('stay_open', False)
        self._min_data_length = kwargs.get(
            'min_data_length', OPENMV_SERIAL_DEFAULT_MIN_DATA_LENGTH)
        self._verbose = kwargs.get('verbose', False)
        super().__init__()
        self.port = kwargs.get('port', find_camera_port())
        self.baudrate = kwargs.get('baudrate', OPENMV_SERIAL_DEFAULT_BAUDRATE)
        self.timeout = kwargs.get('timeout', OPENMV_SERIAL_DEFAULT_TIMEOUT_SEC)


    def read_json(self, retries=OPENMV_SERIAL_DEFAULT_RETRIES):

        def attempt_retry(exception):
            if retries > 0:
                if self._verbose:
                    print('OpenMV retrying read:', retries)
                return self.read_json(retries=retries - 1)
            else:
                raise exception

        if not self.is_open:
            self.open()

        # clear the input buffer of previously sent data
        while self.in_waiting > self._min_data_length:
            self.readline() # reset_input_buffer() doesn't always work...
        # read the next line
        data = self.readline()
        # retry if there's no data
        if not data:
            return attempt_retry(RuntimeError('Camera returned no data'))
        # parse the json
        if self._verbose:
            print(data)
        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError as e:
            return attempt_retry(e)

        if not self._stay_open:
            self.close()
        return data

