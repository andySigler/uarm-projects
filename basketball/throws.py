import random


# the XY position of the basketball hoop
# WARNING: THIS MUST NEVER CHANGE AFTER CREATING THROWING SPECS!!!
HOOP_COORD = {'x': 200, 'y': -200, 'z': 140}

DEFAULT_SPEC = {
    'start_pos': HOOP_COORD.copy(),
    'pause_delay': 0.0,
    'speed': 600.0,
    'acceleration': 20,
    'end_pos': HOOP_COORD.copy(),
    'release_delay': 0.0
}

SPEC_LIST = []


def get_random_throwing_spec():
    specs_copy = [spec.copy() for spec in SPEC_LIST]
    random.shuffle(specs_copy)
    return specs_copy[0].copy()


def get_throwing_spec(idx):
    return SPEC_LIST[idx].copy()


dunk = DEFAULT_SPEC.copy()
SPEC_LIST.append(dunk)

fast_down_center = DEFAULT_SPEC.copy()
fast_down_center['start_pos'] = {'x': 150, 'y': 50, 'z': 50}
fast_down_center['end_pos']['y'] += 40
fast_down_center['end_pos']['x'] += 5
fast_down_center['end_pos']['z'] = 170
fast_down_center['release_delay'] = 0.25
SPEC_LIST.append(fast_down_center)


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
