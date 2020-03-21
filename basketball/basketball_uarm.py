import atexit
import math
import random
import sys
import time

import serial
from uarm import uarm_create, uarm_scan_and_connect

sys.path.append('..')
from utils import openmv_port

from basketball_moves import get_random_throwing_spec, get_throwing_spec
from basketball_moves import throw_ball, show_off
from basketball_moves import HOOP_COORD


def pick_up_ball(bot, ball_pos, hover=20, shuffle_step=3):
    bot.push_settings()
    hover_pos = ball_pos.copy()
    hover_pos['z'] += hover
    bot.move_to(**hover_pos).move_to(**ball_pos).wait_for_arrival()
    bot.pump(True)
    if shuffle_step:
        bot.move_relative(x=-shuffle_step / 2, y=-shuffle_step / 2)
        bot.move_relative(x=shuffle_step).move_relative(y=shuffle_step)
        bot.move_relative(x=-shuffle_step).move_relative(y=-shuffle_step)
        bot.move_relative(x=shuffle_step / 2, y=shuffle_step / 2)
    bot.move_to(**hover_pos).wait_for_arrival()
    bot.pop_settings()


def check_if_picked_up(bot, bot_pos):
    bot.push_settings()
    bot.speed(300).acceleration(5)
    bot.move_to(**bot_pos).wait_for_arrival()
    bot.pop_settings()
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
    bot.move_to(**drop_pos).wait_for_arrival()
    bot.pump(False, sleep=0.3)
    bot.pop_settings()


def wait_for_still_position(camera, data, timeout=None, retries=3):
    print('wait_for_still_position')
    if retries == 0:
        return None
    start_time = time.time()
    while data['moving'] or data['empty']:
        if data['empty']:
            return wait_for_still_position(camera, data, timeout=timeout, retries=retries - 1)
        if timeout and time.time() - start_time > timeout:
            return wait_for_still_position(camera, data, timeout=timeout, retries=retries - 1)
        data = camera.read_json()
    return data


def get_visible_ball(camera, retries=3):
    print('get_visible_ball')
    if retries == 0:
        return None
    data = camera.read_json()
    if data['empty']:
        return get_visible_ball(camera, retries=retries - 1)
    return data


def get_camera_to_mm_multiplier(bot, camera):
    cam_data = get_visible_ball(camera)
    if not cam_data:
        return None
    cam_data = wait_for_still_position(camera, cam_data)
    if not cam_data:
        return None
    mm_test = 50
    bot.push_settings()
    bot.speed(50).acceleration(1)
    rel_cam_data = {}
    for ax in 'xy':
        bot.move_relative(**{ax: mm_test}).wait_for_arrival()
        time.sleep(0.25)
        rel_cam_data[ax] = get_visible_ball(camera)
        bot.move_relative(**{ax: -mm_test}).wait_for_arrival()
    bot.pop_settings()
    if not rel_cam_data['x'] or not rel_cam_data['y']:
        return None
    cam_diff = {
        'x': cam_data['position']['x'] - rel_cam_data['x']['position']['x'],
        'y': cam_data['position']['y'] - rel_cam_data['y']['position']['y']
    }
    cam_to_mm = {
        'x': mm_test / cam_diff['x'],
        'y': mm_test / cam_diff['y']
    }
    return cam_to_mm


def hover_near_ball(bot, camera, cam_to_mm):
    print('hover_near_ball')

    target = {
        'x': 0.2,
        'y': 0.5
    }
    target_thresh = 0.025
    current_pos = None

    def _get_cam_pos():
        cam_data = get_visible_ball(camera)
        if not cam_data:
            return None
        return cam_data['position']


    def _get_cam_dist():
        diff = {ax: target[ax] - current_pos[ax] for ax in 'xy'}
        sums = sum([math.pow(t, 2) for t in diff.values()])
        return math.sqrt(sums)


    def _get_target_mm(step_size=1.0):
        # account for the camera's rotation
        angle = bot.get_base_angle()
        rotated_current_pos = current_pos.copy()
        # TODO: actually implement this...
        # then, stepwise, move closer to to
        diff_cam = {
            'x': target['x'] - rotated_current_pos['x'],
            'y': target['y'] - rotated_current_pos['y']
        }
        diff_mm = {
            'x': diff_cam['x'] * cam_to_mm['x'],
            'y': diff_cam['y'] * cam_to_mm['y']
        }
        move_mm = {
            'x': round(-diff_mm['x'] * step_size, 4),
            'y': round(-diff_mm['y'] * step_size, 4)
        }
        return move_mm


    current_pos = _get_cam_pos()
    while current_pos and _get_cam_dist() > target_thresh:
        print('shifting...')
        target_mm = _get_target_mm(step_size=0.5)
        bot.move_relative(**target_mm).wait_for_arrival()
        current_pos = _get_cam_pos()

    if not current_pos:
        return False

    # move it just slightly, so it's over the ball exactly
    # TODO: fix this Y-offset hack after implementing camera rotation above
    y_offset = bot.position['y'] * 0.15
    final_step = {
        'x': 20,
        'y': y_offset
    }
    bot.move_relative(**final_step)
    return True




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
    ✓ - throw ball at hoop
    ✓ - "dunk" on the hoop

'''


if __name__ == "__main__":

    # position where the camera can observe the most area
    x_start = 145
    x_end = x_start + 65
    y_offset = 120
    z_height = 140
    observer_poses = [
        {'x': x_start, 'y': 0, 'z': z_height},
        {'x': x_start, 'y': y_offset / 2, 'z': z_height},
        {'x': x_start, 'y': y_offset, 'z': z_height},
        {'x': x_end, 'y': y_offset / 2, 'z': z_height},
        {'x': x_end, 'y': 0, 'z': z_height},
        {'x': x_end, 'y': -y_offset / 2, 'z': z_height},
        {'x': x_start, 'y': -y_offset / 2, 'z': z_height}
    ]
    cam_to_mm = {'x': 128.2051282051282, 'y': 87.71929824561403}

    # touches around 39, presses hard around 34
    ball_height = 36

    camera = openmv_port.OpenMVPort(verbose=True)

    robot = uarm_scan_and_connect();
    # robot = uarm_create(simulate=True);
    atexit.register(robot.sleep)

    input_msg = 'Type any letter then ENTER to {0}: '

    if input(input_msg.format('home')):
        robot.home()

    if input(input_msg.format('test functions')):
        idx = 0
        pos = observer_poses[idx]
        robot.move_to(**pos).wait_for_arrival()
        pump_status = False
        while True:
            res = input('m=MOVE, t=TEST_MM, f=FOLLOW, g=SHOWOFF, sN=TEST_SPEC, p=PUMP, h=HOOP: ')
            if res == 'h':
                robot.move_to(**HOOP_COORD).wait_for_arrival()
                pump_status = False
                robot.pump(False)
                robot.move_to(**pos).wait_for_arrival()
            if res == 'p':
                pump_status = not pump_status
                robot.pump(pump_status)
            if res == 'm':
                idx += 1
                if idx >= len(observer_poses):
                    idx = 0
                pos = observer_poses[idx]
                robot.move_to(**pos).wait_for_arrival()
            if res == 't':
                cam_to_mm = get_camera_to_mm_multiplier(robot, camera)
                print(cam_to_mm)
            if res == 'f':
                if hover_near_ball(robot, camera, cam_to_mm):
                    # move down to test
                    robot.move_to(z=ball_height)
                    time.sleep(1)
                    robot.move_to(**pos).wait_for_arrival()
            if res == 'g':
                show_off(robot)
                robot.move_to(**pos).wait_for_arrival()
            if len(res) == 2 and res[0] == 's':
                try:
                    idx = int(res[1])
                    spec = get_throwing_spec(idx)
                    throw_ball(robot, spec)
                    pump_status = False
                except Exception as e:
                    print(e)
                    pass
                robot.move_to(**pos).wait_for_arrival()

    if input(input_msg.format('run automatically')):
        obs_pos_idx = -1
        while True:
            # iterate through the different observer poses
            obs_pos_idx += 1
            if obs_pos_idx >= len(observer_poses):
                obs_pos_idx = 0
            obs_pos = observer_poses[obs_pos_idx]
            robot.push_settings()
            robot.speed(100).acceleration(1.3)
            robot.move_to(**obs_pos).wait_for_arrival()
            robot.pop_settings()
            # time.sleep(1)
            # continue
            # see if there's a visible ball
            cam_data = get_visible_ball(camera)
            if not cam_data:
                continue
            # wait for it to be still
            cam_data = wait_for_still_position(camera, cam_data)
            if not cam_data:
                continue
            if hover_near_ball(robot, camera, cam_to_mm):
                # move down to test
                ball_pos = robot.position
                ball_pos['z'] = ball_height
                # pickup the ball
                pick_up_ball(robot, ball_pos)
                # check with the camera it's picked up
                did_pick_up = check_if_picked_up(robot, obs_pos)
                # drop it
                if did_pick_up:
                    show_off(robot)
                    spec = get_random_throwing_spec()
                    throw_ball(robot, spec)
