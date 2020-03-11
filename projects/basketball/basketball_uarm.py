import atexit
import json
import math
import time

import serial

from openmv_helpers import OpenMV

from uarm import uarm_create, uarm_scan_and_connect


def pick_up_ball(bot, ball_pos, hover=20, shuffle_step=3):
    bot.push_settings()
    hover_pos = ball_pos.copy()
    hover_pos['z'] += hover
    swift.move_to(**hover_pos).move_to(**ball_pos).wait_for_arrival()
    swift.pump(True)
    if shuffle_step:
        swift.move_relative(x=-shuffle_step / 2, y=-shuffle_step / 2)
        swift.move_relative(x=shuffle_step).move_relative(y=shuffle_step)
        swift.move_relative(x=-shuffle_step).move_relative(y=-shuffle_step)
        swift.move_relative(x=shuffle_step / 2, y=shuffle_step / 2)
    swift.move_to(**hover_pos).wait_for_arrival()
    bot.pop_settings()


def drop_ball(bot, drop_pos):
    bot.push_settings()
    swift.move_to(**drop_pos).wait_for_arrival()
    swift.pump(False, sleep=0.3)
    bot.pop_settings()


def throw_ball(bot, spec):
    bot.push_settings()
    bot.speed(50)
    bot.move_to(**spec['start']).wait_for_arrival()
    time.sleep(0.3) # pause before throw
    bot.speed(spec['speed']).acceleration(spec['acceleration'])
    bot.move_to(**spec['end'])
    time.sleep(spec['delay']) # pause before release
    bot.pump(False) # release
    bot.pop_settings()


def save_to_lookup_table(bot, camera, filename):
    cam_pos = None
    ball_pos = None
    bot.move_to(**observer_pos).wait_for_arrival()
    while True:
        # move to the top
        res = input('c=CAM, b=BALL, s=SAVE, x=EXIT')
        if res == 'x':
            bot.move_to(**observer_pos).wait_for_arrival()
            return
        if res == 'c':
            data = camera.read_json()
            print(data)
            cam_pos = data['position']
            continue
        if res == 'b':
            bot.disable_all_motors()
            continue
        if res == 's':
            bot.update_position()
            bot.update_position()
            ball_pos = bot.position
            if cam_pos:
                with open(filename, 'a+') as f:
                    file_line = '{0}, {1}, {2}, {3}, {4}\n'
                    f.write(file_line.format(
                        cam_pos['x'],
                        cam_pos['y'],
                        ball_pos['x'],
                        ball_pos['y'],
                        ball_pos['z']))
            cam_pos = None
            ball_pos = None
            bot.move_to(**observer_pos).wait_for_arrival()
            continue


def parse_lookup_table(filename):
    location_lookup = []
    with open(filename, 'r') as f:
        # OpenMV X, OpenMV Y, uArm X, uArm Y, uArm Z
        f.readline()
        for line in f.readlines():
            line = line.strip()
            line_list = line.split(',')
            openmv = line_list[:2]
            uarm = line_list[2:]
            location_lookup.append({
                'openmv': {
                    'x': float(openmv[0]),
                    'y': float(openmv[1])
                },
                'uarm': {
                    'x': float(uarm[0]),
                    'y': float(uarm[1]),
                    'z': float(uarm[2])
                },
            })
    return location_lookup


def convert_camera_pos_to_uarm_pos(cam_pos, lookup_table):
    # sort by nearest coordinates

    def sort_by_distance(d):
        pos = d['openmv']
        x_diff = cam_pos['x'] - pos['x']
        y_diff = cam_pos['y'] - pos['y']
        return math.sqrt(math.pow(x_diff, 2) + math.pow(y_diff, 2))

    lookup_table = [
        {
            k: v.copy()
            for k, v in d.items()
        }
        for d in lookup_table
    ]
    lookup_table.sort(key=sort_by_distance)
    # using closest neighbors, convert openmv to uarm millimeters
    a = lookup_table[0].copy()
    scaler_x = 0
    scaler_y = 0
    count = 0
    for i in range(1, 10):
        b = lookup_table[i].copy()
        openmv_diff_x = b['openmv']['x'] - a['openmv']['x']
        if openmv_diff_x == 0:
            continue
        openmv_diff_y = b['openmv']['y'] - a['openmv']['y']
        if openmv_diff_y == 0:
            continue
        uarm_diff_x = b['uarm']['x'] - a['uarm']['x']
        uarm_diff_y = b['uarm']['y'] - a['uarm']['y']
        scaler_x += uarm_diff_x / openmv_diff_x
        scaler_y += uarm_diff_y / openmv_diff_y
        count += 1
    scaler_x = scaler_x / count
    scaler_y = scaler_y / count
    # using millimeter conversion, and openmv offset, get uarm position
    openmv_offset_x = cam_pos['x'] - a['openmv']['x']
    openmv_offset_y = cam_pos['y'] - a['openmv']['y']
    uarm_offset_x = openmv_offset_x * scaler_x
    uarm_offset_y = openmv_offset_y * scaler_y
    real_pos = a['uarm'].copy()
    real_pos['x'] += uarm_offset_x
    real_pos['y'] += uarm_offset_y
    return real_pos


def get_ball_pos(camera, lookup_table, ball_height, retries=3):
    cam_data = camera.read_json()
    if cam_data['empty']:
        if retries > 0:
            return get_ball_pos(
                camera, lookup_table, ball_height, retries=retries - 1)
        raise RuntimeError('Camera does not see a ball')
    ball_pos = convert_camera_pos_to_uarm_pos(
        cam_data['position'], lookup_table)
    ball_pos['z'] = ball_height
    return ball_pos


def can_pick_up_ball(camera):
    cam_data = camera.read_json()
    if cam_data['empty']:
        return False
    if cam_data['moving']:
        return False
    return True


def wait_for_ball(camera, timeout=None):
    start_time = time.time()
    while not can_pick_up_ball(camera):
        if timeout and time.time() - start_time > timeout:
            raise RuntimeError('Timed out waiting or ball')


'''
Overview:

1) uarm scans for ball with camera
    - [OpenMV] find orange blob
    - [OpenMV] print blob coordinate
    {
        "empty": true || false,
        "moving": true || false,
        "position": {
            "y": 0.0-1.0,
            "x": 0.0-1.0
        }
    }
    - wait for blob to slow

2) uarm picks up ball
    - convert blob locaton to uarm location
    - hover over and pick up
    - move up and test the blob is gone

3) uarm throws ball
    - do some cool movements
    - throw ball at hoop
    - "dunk" on the hoop

'''


if __name__ == "__main__":

    # position where the camera can observe the entire drawing surface
    observer_pos = {'x': 145, 'y': 0, 'z': 140}

    # touches around 39, presses hard around 34
    ball_height = 36

    thow_spec = {
        'start': {'x': 130, 'y': -140, 'z': ball_height + 5},
        'end': {'x': 130, 'y': 140, 'z': 145},
        'speed': 600,
        'acceleration': 30,
        'delay': 0.3
    }

    lookup_filename = 'ball_to_uarm.csv'
    location_lookup = parse_lookup_table(lookup_filename)

    camera = OpenMV()

    swift = uarm_scan_and_connect();
    # swift = uarm_create(simulate=True);
    atexit.register(swift.sleep)

    input_msg = 'Type any letter then ENTER to {0}: '

    if input(input_msg.format('home')):
        swift.home()

    if input(input_msg.format('observe')):
        swift.move_to(**observer_pos).wait_for_arrival().disable_base()
        while True:
            input('Press ENTER to move to PUMP: ')
            swift.pump(True)
            input('Press ENTER to move to NOT pump: ')
            swift.pump(False)

    if input(input_msg.format('test track & pickup')):
        while True:
            swift.move_to(**observer_pos).wait_for_arrival().disable_base()
            wait_for_ball(camera)
            ball_pos = get_ball_pos(camera, location_lookup, ball_height)
            pick_up_ball(swift, ball_pos)
            time.sleep(1)
            drop_ball(swift, ball_pos)

    if input(input_msg.format('save ball')):
        save_to_lookup_table(swift, camera, lookup_filename)

    swift.sleep()
