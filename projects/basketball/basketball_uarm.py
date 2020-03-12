import atexit
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


def check_if_picked_up(bot, bot_pos):
    bot.move_to(**bot_pos).wait_for_arrival()
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


def wait_for_still_position(camera, data, timeout=None):
    print('wait_for_still_position')
    start_time = time.time()
    while data['moving'] or data['empty']:
        if data['empty']:
            return None
        if timeout and time.time() - start_time > timeout:
            return None
        data = camera.read_json()
    return data


def move_closer_to_ball(bot, camera, data):
    print('move_closer_to_ball')
    # TODO: move closer to the ball, to make camera angle better
    return data


def get_visible_ball(camera):
    print('get_visible_ball')
    data = camera.read_json()
    if data['empty']:
        return None
    return data


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
    observer_poses = [
        {'x': 145, 'y': 0, 'z': 140}
    ]

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
        swift.move_to(**observer_poses[0]).wait_for_arrival()
        swift.disable_base()
        while True:
            input('Press ENTER to turn pump ON: ')
            swift.pump(True)
            input('Press ENTER to turn pump OFF: ')
            swift.pump(False)

    if input(input_msg.format('test track & pickup')):
        obs_pos_idx = 0
        while True:
            # iterate through the different observer poses
            obs_pos = observer_poses[obs_pos_idx]
            obs_pos_idx += 1
            if obs_pos_idx >= len(observer_poses):
                obs_pos_idx = 0
            swift.move_to(**obs_pos).wait_for_arrival().disable_base()
            # see if there's a visible ball
            cam_data = get_visible_ball(camera)
            if not cam_data:
                continue
            # move closer to it to make pickup easier
            cam_data = move_closer_to_ball(swift, camera, cam_data)
            if not cam_data:
                continue
            # wait for it to be still
            cam_data = wait_for_still_position(camera, cam_data)
            if not cam_data:
                continue
            # convert camera data to actual pickup position
            ball_pos = location_lookup.convert(
                cam_data['position'], swift.position, table)
            ball_pos['z'] = ball_height
            # pickup the ball
            pick_up_ball(swift, ball_pos)
            # check with the camera it's picked up
            did_pick_up = check_if_picked_up(swift, obs_pos)
            # drop it
            if did_pick_up:
                drop_ball(swift, ball_pos)

    if input(input_msg.format('generate lookup table')):
        location_lookup.generate(swift, camera, table_filename, observer_poses[0])

    swift.sleep()
