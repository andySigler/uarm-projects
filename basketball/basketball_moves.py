import copy
import math
import random
import time

from uarm.wrapper.swift_api_wrapper import UARM_MAX_SPEED


# the XY position of the basketball hoop
# WARNING: THIS MUST NEVER CHANGE AFTER CREATING THROWING SPECS!!!
HOOP_COORD = {'x': 200, 'y': -200, 'z': 140}
SHOW_OFF_START = {'x': 200, 'y': 100, 'z': 40}

DEFAULT_SPEC = {
    'start_pos': HOOP_COORD.copy(),
    'pause_delay': 0.0,
    'speed': UARM_MAX_SPEED,
    'acceleration': 20,
    'end_pos': HOOP_COORD.copy(),
    'release_delay': 0.0
}

SPEC_LIST = []


def get_random_throwing_spec():
    random_order = [spec for spec in SPEC_LIST]
    random.shuffle(random_order)
    return copy.deepcopy(random_order[0])


def get_throwing_spec(idx):
    return copy.deepcopy(SPEC_LIST[idx])


def throw_ball(bot, spec):
    bot.push_settings()
    if spec['start_pos'] and not bot.can_move_to(**spec['start_pos']):
        raise RuntimeError('Can not move to: ', spec['start_pos'])
    if spec['end_pos'] and not bot.can_move_to(**spec['end_pos']):
        raise RuntimeError('Can not move to: ', spec['end_pos'])
    if spec['start_pos']:
        bot.move_to(**spec['start_pos']).wait_for_arrival()
        time.sleep(spec.get('pause_delay', 0))
    if spec['end_pos']:
        bot.speed(spec['speed']).acceleration(spec['acceleration'])
        bot.move_to(**spec['end_pos'])
    r_del = spec.get('release_delay')
    if r_del:
        time.sleep(spec.get('release_delay', 0))
    else:
        bot.wait_for_arrival()
    bot.pump(False, sleep=0)
    bot.pop_settings()


def show_off(bot):
    bot.push_settings()
    bot.speed(200).acceleration(1).move_to(**SHOW_OFF_START).wait_for_arrival()
    bot.acceleration(15)
    time.sleep(random.random() * 0.5 + 0.25)
    counter = 0
    while counter < 20:
        start_pos = bot.position
        target_pos = get_random_show_off_pos(start_pos)
        # change speed
        speed_max = 550
        speed_min = 300
        if target_pos['y'] > start_pos['y']:
            speed_max = 300
            speed_min = 100
        speed_range = speed_max - speed_min
        speed_scaler = math.pow(random.random(), 1)
        speed = speed_min + (speed_scaler * speed_range)

        bot.speed(speed)
        bot.move_to(**target_pos)
        # move back to previous position (juke)
        if counter > 3 and random.random() < 0.3:
            bot.move_to(**start_pos)
        # stop showing off
        if random.random() < 0.1:
            break
        else:
            counter += 1
    bot.pop_settings()


def get_random_show_off_pos(pos):
    pos_min = {
        'x': 130,
        'y': 0,
        'z': 45
    }
    pos_max = {
        'x': 180,
        'y': 150,
        'z': 60
    }
    return {
        ax: random.randint(pos_min[ax], pos_max[ax])
        for ax in 'xyz'
    }


dunk = copy.deepcopy(DEFAULT_SPEC)
dunk['start_pos'] = None
SPEC_LIST.append(dunk)

fast_down_center = copy.deepcopy(DEFAULT_SPEC)
fast_down_center['start_pos'] = {'x': 150, 'y': 50, 'z': 50}
fast_down_center['end_pos']['x'] += 5
fast_down_center['end_pos']['y'] += 50
fast_down_center['end_pos']['z'] = 170
fast_down_center['release_delay'] = 0.23
SPEC_LIST.append(fast_down_center)

# angle_shot = copy.deepcopy(DEFAULT_SPEC)
# angle_shot['start_pos'] = {'x': 100, 'y': -100, 'z': 40}
# angle_shot['end_pos']['x'] -= 40
# angle_shot['end_pos']['y'] += 5
# angle_shot['end_pos']['z'] = 170
# angle_shot['acceleration'] = 25
# angle_shot['release_delay'] = 0.15
# SPEC_LIST.append(angle_shot)


if __name__ == "__main__":
    from uarm import uarm_scan_and_connect

    robot = uarm_scan_and_connect()
    robot.disable_all_motors()

    print('Testing all throwing spec coordinates can be ran on robot')
    for i, spec in enumerate(SPEC_LIST):
        if not robot.can_move_to(**spec['start_pos']):
            raise Exception(
                'Spec at index={0} failed: {1}', i, spec['start_pos'])
        if not robot.can_move_to(**spec['end_pos']):
            raise Exception(
                'Spec at index={0} failed: {1}', i, spec['end_pos'])
    print('PASS')
