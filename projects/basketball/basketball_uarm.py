import atexit
import json
import math
import sys
import time

import serial

from uarm import uarm_create, uarm_scan_and_connect

sys.path.append('..')
from projects_utils import openmv_port
import location_lookup


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


def check_if_picked_up(bot, observer_pos):
    bot.move_to(**observer_pos).wait_for_arrival()
    picked_up = True
    for i in range(3):
        cam_data = camera.read_json()
        if not cam_data['empty']:
            picked_up = False
            break
    if not picked_up:
        bot.pump(False, sleep=0)
    return picked_up



def drop_ball(bot, drop_pos):
    bot.push_settings()
    swift.move_to(**drop_pos).wait_for_arrival()
    swift.pump(False, sleep=0.3)
    bot.pop_settings()


def throw_ball(bot, spec):
    '''
    {
        'start_pos': {'x': 0, 'y': 0, 'z': 0},
        'pause_delay': float,
        'speed': float,
        'acceleration': float,
        'end_pos': {'x': 0, 'y': 0, 'z': 0},
        'release_delay': float
    }
    '''
    bot.push_settings()
    bot.move_to(**spec['start_pos']).wait_for_arrival()
    time.sleep(spec.get('pause_delay', 0))
    bot.speed(spec['speed']).acceleration(spec['acceleration'])
    bot.waiting_ready().move_to(**spec['end_pos'])
    time.sleep(spec.get('release_delay', 0))
    bot.pump(False, sleep=0)
    bot.pop_settings()


def get_ball_pos(camera, lookup_table, retries=3):
    '''
    cam_data = {
        "empty": true || false,
        "moving": true || false,
        "position": {
            "y": 0.0-1.0,
            "x": 0.0-1.0
        }
    }
    '''
    cam_data = camera.read_json()
    if cam_data['empty']:
        if retries > 0:
            return get_ball_pos(
                camera, lookup_table, retries=retries - 1)
        raise RuntimeError('Camera does not see a ball')
    ball_pos = location_lookup.convert(cam_data['position'], lookup_table)
    return ball_pos


def can_pick_up_ball(camera):
    cam_data = camera.read_json()
    if cam_data['empty']:
        return False
    if cam_data['moving']:
        return False
    return True


def wait_for_still_ball(camera, timeout=None):
    start_time = time.time()
    while not can_pick_up_ball(camera):
        if timeout and time.time() - start_time > timeout:
            raise RuntimeError('Timed out waiting or ball')


'''
Overview:

1) uarm scans for ball with camera
    ✓ - [OpenMV] find orange blob
    ✓ - [OpenMV] print blob coordinate
    ✓ - wait for blob to slow

2) uarm picks up ball
    ✓ - convert blob locaton to uarm location
    ✓ - hover over and pick up
    ✓ - move up and test the blob is gone

3) uarm throws ball
    - do some cool movements
    - throw ball at hoop
    - "dunk" on the hoop

'''


if __name__ == "__main__":

    # position where the camera can observe the most area
    observer_pos = {'x': 145, 'y': 0, 'z': 140}

    # touches around 39, presses hard around 34
    ball_height = 36

    table_filename = 'openmv_to_uarm.csv'
    table = location_lookup.load(table_filename)

    camera = openmv_port.OpenMVPort(verbose=True)

    swift = uarm_scan_and_connect();
    # swift = uarm_create(simulate=True);
    atexit.register(swift.sleep)

    input_msg = 'Type any letter then ENTER to {0}: '

    if input(input_msg.format('home')):
        swift.home()

    if input(input_msg.format('observe')):
        swift.move_to(**observer_pos).wait_for_arrival().disable_base()
        while True:
            input('Press ENTER to turn pump ON: ')
            swift.pump(True)
            input('Press ENTER to turn pump OFF: ')
            swift.pump(False)

    if input(input_msg.format('test track & pickup')):
        while True:
            swift.move_to(**observer_pos).wait_for_arrival().disable_base()
            wait_for_still_ball(camera)
            ball_pos = get_ball_pos(camera, table)
            ball_pos['z'] = ball_height
            pick_up_ball(swift, ball_pos)
            did_pick_up = check_if_picked_up(swift, observer_pos)
            if did_pick_up:
                drop_ball(swift, ball_pos)

    if input(input_msg.format('generate lookup table')):
        location_lookup.generate(swift, camera, table_filename)

    swift.sleep()
