import math
import time

from uarm_helpers import uarm_scan_and_connect, SwiftAPIExtended

swift = uarm_scan_and_connect(verbose=True);
swift.speed_percentage(1)
swift.acceleration(10)
swift.home()
swift.safe_disable_motors()

# dist = 30
# for i in range(3):
#     swift.move_relative(y=dist).move_relative(x=dist).move_relative(z=dist)
#     swift.move_relative(y=-dist).move_relative(x=-dist).move_relative(z=-dist)

swift.wait(timeout=10)

# while True:
#     time.sleep(0.5)
#     print(swift.get_position(wait=True))
