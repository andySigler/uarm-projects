import math
import os
import sys
import time

from uarm import uarm_create, uarm_scan_and_connect

# swift = uarm_scan_and_connect();
swift = uarm_create(simulate=True);

swift.home()

swift.speed(500).acceleration(30)

dist = 100
tot_dist = 0
start = time.time()
for i in range(1):
    swift.move_relative(x=dist)
    swift.move_relative(x=-dist)
    tot_dist += dist * 2
swift.wait_for_arrival()
time_diff = round(time.time() - start, 3)
print('X', tot_dist, time_diff)

dist = 200
tot_dist = 0
swift.move_relative(x=50).move_relative(y=-dist/2).wait_for_arrival()
start = time.time()
for i in range(1):
    swift.move_relative(y=dist)
    swift.move_relative(y=-dist)
    tot_dist += dist * 2
swift.wait_for_arrival()
time_diff = round(time.time() - start, 3)
print('Y', tot_dist, time_diff)

dist = 100
tot_dist = 0
start = time.time()
for i in range(1):
    swift.move_relative(z=dist)
    swift.move_relative(z=-dist)
    tot_dist += dist * 2
swift.wait_for_arrival()
time_diff = round(time.time() - start, 3)
print('Z', tot_dist, time_diff)

# swift.sleep()
