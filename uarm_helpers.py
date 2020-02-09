import time

from serial.tools.list_ports import comports
from uarm.wrapper import SwiftAPI


UARM_USB_HWID = '2341:0042'

UARM_MAX_SPEED = 250
UARM_MIN_SPEED = 1

UARM_MAX_ACCELERATION = 50
UARM_MIN_ACCELERATION = 0.01

UARM_DEFAULT_SPEED = UARM_MAX_SPEED / 2
UARM_DEFAULT_ACCELERATION = 1.3

UARM_SAFE_SPEED = 20
UARM_SAFE_ACCELERATION = UARM_DEFAULT_ACCELERATION

UARM_X_MIN = 105

UARM_SAFE_POS = {
  'x': 110, 'y': 0, 'z': 40
}


def _serial_print_port_info(port_info):
  print('- Port: {0}'.format(port_info.device))
  for key, val in port_info.__dict__.items():
    if (key != 'device' and val and val != 'n/a'):
      print('\t- {0}: {1}'.format(key, val))


def _serial_attempt_connect(port_info, verbose=False):
  if (port_info.hwid and UARM_USB_HWID in port_info.hwid):
    try:
      swift = SwiftAPIExtended(
        filters={'hwid': port_info.hwid}, do_not_open=True, verbose=verbose)
      swift.connect()
      swift.wait()
      return swift
    except Exception as e:
      print(e)
      return None


def uarm_scan_and_connect(verbose=False):
  if verbose:
    print('Searching for uArm serial port')
  for p in comports():
    if verbose:
      _serial_print_port_info(p)
    swift = _serial_attempt_connect(p, verbose=verbose)
    if swift:
      if verbose:
        print('Connected to uArm on port: {0}'.format(p.device))
        for key, val in swift.get_device_info().items():
          print('\t- {0}: {1}'.format(key, val))
      return swift
  raise RuntimeError('Unable to find uArm port')


class SwiftAPIExtended(SwiftAPI):

  def __init__(self, **kwargs):
    self._modes = {
      'general': 0,
      'laser': 1,
      '3d_printer': 2,
      'pen_gripper': 3
    }
    self._motor_ids = {
      'base': 0,
      'shoulder': 1,
      'elbow': 2,
      'servo': 3
    }
    self._speed = UARM_DEFAULT_SPEED
    self._acceleration = UARM_DEFAULT_ACCELERATION
    self._pos = {'x': 0, 'y': 0, 'z': 0} # run self.home() to get real position
    super().__init__(**kwargs)

  def log_verbose(self, msg):
    if self._verbose:
      print(msg)

  '''
  SETTINGS and MODES
  '''

  def wait(self, timeout=5):
    self.waiting_ready(timeout=5)

  def mode_general(self):
    self.log_verbose('mode_general')
    self.set_mode(self._modes['general'])
    return self

  def speed(self, speed):
    self.log_verbose('speed: {0}'.format(speed))
    if speed < UARM_MIN_SPEED:
      speed = UARM_MIN_SPEED
      self.log_verbose('speed changed to: {0}'.format(speed))
    if speed > UARM_MAX_SPEED:
      speed = UARM_MAX_SPEED
      self.log_verbose('speed changed to: {0}'.format(speed))
    self._speed = speed
    return self

  def speed_percentage(self, percentage):
    self.log_verbose('speed_percentage: {0}'.format(percentage))
    if percentage < 0:
      percentage = 0
    if percentage > 100:
      percentage = 100
    speed = (UARM_MAX_SPEED - UARM_MIN_SPEED) * percentage
    speed +=  UARM_MIN_SPEED
    self.speed(speed)
    return self

  def acceleration(self, acceleration):
    self.log_verbose('acceleration: {0}'.format(acceleration))
    if acceleration < UARM_MIN_ACCELERATION:
      acceleration = UARM_MIN_ACCELERATION
      self.log_verbose('acceleration changed to: {0}'.format(acceleration))
    if acceleration > UARM_MAX_ACCELERATION:
      acceleration = UARM_MAX_ACCELERATION
      self.log_verbose('acceleration changed to: {0}'.format(acceleration))
    self._acceleration = acceleration
    self.set_acceleration(acc=self._acceleration)
    return self

  def read_and_save_position(self):
    self.log_verbose('read_and_save_position')
    pos = self.get_position(wait=True)
    self._pos = {'x': pos[0], 'y': pos[1], 'z': pos[2]}
    self.log_verbose('New Position: {0}'.format(self._pos))

  '''
  LEVEL 1 COMMANDS
  '''

  def home(self, mode='general'):
    self.log_verbose('home')
    self.flush_cmd()
    self.wait()
    self.set_speed_factor(1.0)
    self.mode_general()
    self.reset(speed=self._speed, wait=True)
    self.speed(self._speed)
    self.acceleration(self._acceleration)
    time.sleep(0.05)
    self.read_and_save_position()
    return self

  def move_to(self, x=None, y=None, z=None, wait=False):
    self.log_verbose('move_to: x={0}, y={1}, z={2}'.format(x, y, z))
    if x < UARM_X_MIN:
      x = UARM_X_MIN
    self.set_position(
      x=x, y=y, z=z, relative=False, speed=self._speed, wait=wait)
    if x is not None:
      self._pos['x'] = x
    if y is not None:
      self._pos['y'] = y
    if z is not None:
      self._pos['z'] = z
    return self

  def move_relative(self, x=None, y=None, z=None, wait=False):
    self.log_verbose('move_relative: x={0}, y={1}, z={2}'.format(x, y, z))
    kwargs = {'wait': wait}
    if x is not None:
      kwargs['x'] = x + self._pos['x']
    if y is not None:
      kwargs['y'] = y + self._pos['y']
    if z is not None:
      kwargs['z'] = z + self._pos['z']
    # using only absolute movements, because accelerations do not seem to take
    # affect when using relative movements with the API
    self.move_to(**kwargs)
    return self

  def disable_motor_base(self):
    self.log_verbose('disable_motor_base')
    self.set_servo_detach(self._motor_ids['base'])
    return self

  def disable_motor_all(self):
    self.log_verbose('disable_motor_all')
    self.set_servo_detach(None)
    return self

  def enable_motor_base(self):
    self.log_verbose('enable_motor_base')
    self.set_servo_attach(self._motor_ids['base'])
    read_and_save_position()
    return self

  def enable_motor_all(self):
    self.log_verbose('enable_motor_all')
    self.set_servo_attach(None)
    read_and_save_position()
    return self

  '''
  LEVEL 2 COMMANDS
  '''

  def safe_disable_motors(self):
    self.log_verbose('safe_disable_motors')
    old_speed = float(self._speed)
    old_accel = float(self._acceleration)
    self.speed(UARM_SAFE_SPEED)
    self.acceleration(UARM_SAFE_ACCELERATION)
    self.move_to(**UARM_SAFE_POS)
    self.speed(old_speed)
    self.acceleration(old_accel)
    self.disable_motor_all()
    return self
