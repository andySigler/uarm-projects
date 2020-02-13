import time

from serial.tools.list_ports import comports
from uarm.wrapper import SwiftAPI


# SERIAL PORT
UARM_USB_HWID = '2341:0042'

# MODE (end-tool)
UARM_DEFAULT_MODE = 'general'

# SPEED
UARM_MAX_SPEED = 250
UARM_MIN_SPEED = 1
UARM_DEFAULT_SPEED = UARM_MAX_SPEED / 2

# ACCELERATION
UARM_MAX_ACCELERATION = 50
UARM_MIN_ACCELERATION = 0.01
UARM_DEFAULT_ACCELERATION = 5

# WRIST ANGLE
UARM_MIN_WRIST_ANGLE = 0
UARM_MAX_WRIST_ANGLE = 180
UARM_DEFAULT_WRIST_ANGLE = 90
UARM_DEFAULT_WRIST_SLEEP = 0.25

# PUMP & GRIP
UARM_DEFAULT_PUMP_SLEEP = {True: 0.2, False: 0.2}
UARM_DEFAULT_GRIP_SLEEP = {True: 0, False: 2.0}
UARM_HOLDING_CODES = ['off', 'empty', 'holding']

# COORDINATE MODES
UARM_MODE_TO_CODE = {
  'general': 0,
  # 'laser': 1,
  # '3d_printer': 2,
  'pen_gripper': 3
}
UARM_CODE_TO_MODE = {
  val: key
  for key, val in UARM_MODE_TO_CODE.items()
}

# HOMING
UARM_HOME_SPEED = 10
UARM_HOME_ACCELERATION = 1.3
UARM_HOME_ORDER = [0, 1, 2] # base=0, shoulder=1, elbow=2
UARM_HOME_ANGLE = [90.0, 118, 50]

# PROBING
UARM_DEFAULT_PROBE_SPEED = 10
UARM_DEFAULT_PROBE_ACCELERATION = 1.3
UARM_DEFAULT_PROBE_STEP = 1


def _serial_print_port_info(port_info):
  print('- Port: {0}'.format(port_info.device))
  for key, val in port_info.__dict__.items():
    if (key != 'device' and val and val != 'n/a'):
      print('\t- {0}: {1}'.format(key, val))


def _serial_attempt_connect(port_info, verbose=False, verbose_serial=False):
  if (port_info.hwid and UARM_USB_HWID in port_info.hwid):
    try:
      swift = SwiftAPIExtended(
        filters={'hwid': port_info.hwid},
        verbose=verbose,
        verbose_serial=verbose_serial)
      return swift
    except Exception as e:
      print(e)
      return None


def uarm_scan_and_connect(verbose=False, verbose_serial=False):
  if verbose:
    print('Searching for uArm serial port')
  for p in comports():
    if verbose:
      _serial_print_port_info(p)
    swift = _serial_attempt_connect(
      p, verbose=verbose, verbose_serial=verbose_serial)
    if swift:
      if verbose:
        print('Connected to uArm on port: {0}'.format(p.device))
        for key, val in swift.get_device_info().items():
          print('\t- {0}: {1}'.format(key, val))
      return swift
  raise RuntimeError('Unable to find uArm port')


class SwiftAPIExtended(SwiftAPI):

  def __init__(self, **kwargs):
    self._mode_str = UARM_DEFAULT_MODE
    self._mode_code = UARM_MODE_TO_CODE[self._mode_str]
    self._motor_ids = {
      'base': 0,
      'shoulder': 1,
      'elbow': 2,
      'wrist': 3
    }
    self._speed = UARM_DEFAULT_SPEED
    self._acceleration = UARM_DEFAULT_ACCELERATION
    self._wrist_angle = UARM_DEFAULT_WRIST_ANGLE
    self._pos = {'x': 0, 'y': 0, 'z': 0} # run self.home() to get real position
    super().__init__(**kwargs) # raises Exception if port is incorrect
    self.setup()

  def _log_verbose(self, msg):
    if self._verbose:
      print(msg)

  '''
  SETTINGS and MODES
  '''

  def setup(self):
    self._log_verbose('setup')
    self.flush_cmd()
    self.waiting_ready()
    self.set_speed_factor(1.0)
    self.mode(self._mode_str)
    return self

  def wait_for_arrival(self, timeout=5):
    self._log_verbose('wait')
    start_time = time.time()
    self.waiting_ready(timeout=timeout)
    while time.time() - start_time < timeout:
      # sending these commands while moving will make uArm much less smooth
      self.move_to(**self._pos)
      time.sleep(0.2)
      if not self.get_is_moving(wait=True):
        return self
    raise TimeoutError(
      'Unable to reach target position {0} within {1} seconds'.format(
        self._pos, timeout))

  def mode(self, new_mode):
    self._log_verbose('mode: {0}'.format(new_mode))
    if new_mode not in UARM_MODE_TO_CODE.keys():
      raise ValueError('Unknown mode: {0}'.format(new_mode))
    self._mode_str = new_mode
    self._mode_code = UARM_MODE_TO_CODE[self._mode_str]
    self.set_mode(UARM_MODE_TO_CODE[self._mode_str])
    self.update_position()
    return self

  def speed(self, speed):
    self._log_verbose('speed: {0}'.format(speed))
    if speed < UARM_MIN_SPEED:
      speed = UARM_MIN_SPEED
      self._log_verbose('speed changed to: {0}'.format(speed))
    if speed > UARM_MAX_SPEED:
      speed = UARM_MAX_SPEED
      self._log_verbose('speed changed to: {0}'.format(speed))
    self._speed = speed
    return self

  def speed_percentage(self, percentage):
    self._log_verbose('speed_percentage: {0}'.format(percentage))
    if percentage < 0:
      percentage = 0
    if percentage > 100:
      percentage = 100
    speed = (UARM_MAX_SPEED - UARM_MIN_SPEED) * percentage
    speed +=  UARM_MIN_SPEED
    self.speed(speed)
    return self

  def acceleration(self, acceleration):
    self._log_verbose('acceleration: {0}'.format(acceleration))
    if acceleration < UARM_MIN_ACCELERATION:
      acceleration = UARM_MIN_ACCELERATION
      self._log_verbose('acceleration changed to: {0}'.format(acceleration))
    if acceleration > UARM_MAX_ACCELERATION:
      acceleration = UARM_MAX_ACCELERATION
      self._log_verbose('acceleration changed to: {0}'.format(acceleration))
    self._acceleration = acceleration
    self.set_acceleration(acc=self._acceleration)
    return self

  def update_position(self):
    self._log_verbose('update_position')
    pos = self.get_position(wait=True)
    self._pos = {
      'x': round(pos[0], 2),
      'y': round(pos[1], 2),
      'z': round(pos[2], 2)
    }
    self._log_verbose('New Position: {0}'.format(self._pos))
    return self

  @property
  def position(self):
    return self._pos

  '''
  ATOMIC COMMANDS
  '''

  def move_to(self, x=None, y=None, z=None):
    self._log_verbose('move_to: x={0}, y={1}, z={2}'.format(x, y, z))
    if x is not None:
      self._pos['x'] = round(x, 2)
    if y is not None:
      self._pos['y'] = round(y, 2)
    if z is not None:
      self._pos['z'] = round(z, 2)
    self.set_position(relative=False, speed=self._speed, **self._pos)
    return self

  def move_relative(self, x=None, y=None, z=None):
    self._log_verbose('move_relative: x={0}, y={1}, z={2}'.format(x, y, z))
    kwargs = {}
    if x is not None:
      kwargs['x'] = round(x + self._pos['x'], 2)
    if y is not None:
      kwargs['y'] = round(y + self._pos['y'], 2)
    if z is not None:
      kwargs['z'] = round(z + self._pos['z'], 2)
    # using only absolute movements, because accelerations do not seem to take
    # affect when using relative movements with the API
    self.move_to(**kwargs)
    return self

  def rotate_to(self, angle=UARM_DEFAULT_WRIST_ANGLE,
                sleep=UARM_DEFAULT_WRIST_SLEEP, wait=True):
    self._log_verbose('rotate_to')
    if angle < UARM_MIN_WRIST_ANGLE:
      angle = UARM_MIN_WRIST_ANGLE
      self._log_verbose('angle changed to: {0}'.format(angle))
    if angle > UARM_MAX_WRIST_ANGLE:
      angle = UARM_MAX_WRIST_ANGLE
      self._log_verbose('angle changed to: {0}'.format(angle))
    self._wrist_angle = angle
    # previous move command will return before it has arrived at destination
    if wait:
      self.wait_for_arrival()
    # speed has no affect, b/c servo motors are controlled by PWM
    # so from the device's perspective, the change is instantaneous
    self.set_wrist(angle=angle)
    time.sleep(sleep)
    return self

  def rotate_relative(self, angle=0, sleep=UARM_DEFAULT_WRIST_SLEEP,
                      wait=True):
    self._log_verbose('rotate_relative')
    angle = self._wrist_angle + angle
    self.rotate_to(angle=angle, sleep=sleep, wait=wait)
    return self

  def disable_motor_base(self):
    self._log_verbose('disable_motor_base')
    self.set_servo_detach(self._motor_ids['base'], wait=True)
    return self

  def disable_all_motors(self):
    self._log_verbose('disable_all_motors')
    self.set_servo_detach(None, wait=True)
    return self

  def enable_motor_base(self):
    self._log_verbose('enable_motor_base')
    self.set_servo_attach(self._motor_ids['base'], wait=True)
    # update position, b/c no way to know where we are
    self.update_position()
    return self

  def enable_all_motors(self):
    self._log_verbose('enable_all_motors')
    self.set_servo_attach(None, wait=True)
    # update position, b/c no way to know where we are
    self.update_position()
    return self

  def pump(self, enable, sleep=None):
    self._log_verbose('pump: {0}'.format(enable))
    if self._mode_str != 'general':
      raise RuntimeError(
        'Must be in \"general\" to user pump')
    ret = self.set_pump(enable, wait=True, check=True)
    if sleep is None:
      sleep = UARM_DEFAULT_PUMP_SLEEP[enable]
    time.sleep(sleep)
    return self

  def grip(self, enable, sleep=None):
    self._log_verbose('grip: {0}'.format(enable))
    if self._mode_str != 'pen_gripper':
      raise RuntimeError(
        'Must be in \"pen_gripper\" to user gripper')
    ret = self.set_gripper(enable, wait=True, check=True)
    if sleep is None:
      sleep = UARM_DEFAULT_GRIP_SLEEP[enable]
    time.sleep(sleep)
    return self

  def is_pressing(self):
    self._log_verbose('is_pressing')
    if self._mode_str != 'general':
      raise RuntimeError(
        'Must be in \"general\" mode to test if pressing something')
    return self.get_limit_switch(wait=True)

  '''
  COMBINATORY COMMANDS
  '''

  def home(self, mode='general'):
    self._log_verbose('home')
    _speed = float(self._speed)
    _accel = float(self._acceleration)
    self.speed(UARM_HOME_SPEED)
    self.acceleration(UARM_HOME_ACCELERATION)
    self.rotate_to(UARM_DEFAULT_WRIST_ANGLE)
    # move to the "safe" position, where it is safe to disable all motors
    # using angles ensures it's the same regardless of mode (coordinate system)
    for m_id in UARM_HOME_ORDER:
      self.set_servo_angle(servo_id=m_id, angle=UARM_HOME_ANGLE[m_id], wait=True)
    self.speed(_speed)
    self.acceleration(_accel)
    # b/c using servo angles, Python has lost track of where XYZ are
    time.sleep(0.25) # give it an extra time to ensure position is settled
    self.update_position()
    return self

  def probe(self, step=UARM_DEFAULT_PROBE_STEP, speed=UARM_DEFAULT_PROBE_SPEED):
    self._log_verbose('probe')
    _speed = float(self._speed)
    self.speed(speed)
    # move down until we hit the limit switch
    while not self.is_pressing():
      self.move_relative(z=-step).wait_for_arrival()
    self.speed(_speed)
    return self