import math
import os
import sys
import time

from uarm import uarm_create, uarm_scan_and_connect


def pos_cb(pos):
    print(pos)


# swift = uarm_scan_and_connect();
swift = uarm_create(simulate=True);
swift.home()
# swift.disable_all_motors()

# swift.register_report_position_callback(callback=pos_cb)
# swift.set_report_position(interval=0.1)

while True:
    time.sleep(1)
    swift.move_to(**{'x': 200, 'y': 40, 'z': 120})
    time.sleep(1)
    swift.move_to(**{'x': 130, 'y': -40, 'z': 40})
