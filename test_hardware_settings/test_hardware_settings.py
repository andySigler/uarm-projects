import logging
import time

from uarm import uarm_scan_and_connect, uarm_create


# osc_logger = logging.getLogger('uarm')
# osc_logger.setLevel(logging.DEBUG)
# ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# ch.setFormatter(formatter)
# osc_logger.addHandler(ch)

robot = uarm_scan_and_connect()
# robot.hardware_settings_reset()

robot.home()

# robot.rotate_to(105)
# robot.wrist_is_centered()

# robot.disable_all_motors()
# input('RREADy')
# robot.z_is_level()

# robot.home()
robot.move_to(x=150).move_to(z=0)
