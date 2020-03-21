import atexit
import json
import math
import random
import sys
import time

import serial

from uarm import uarm_scan_and_connect

sys.path.append('..')
from utils import openmv_port

# speeds
move_speed = 400
move_accel = 5
draw_speed = 200
draw_accel = 3

# Z position of where pen touches paper
# found through `find_paper_height()`
paper_height = 23

# position where the camera can observe the entire drawing surface
observer_pos = {'x': 145, 'y': 0, 'z': 140}

# for some reason, uArm's wrist angle isn't exactly centered at 90 degrees
wrist_centered_angle = 100

# height at which it is safe to move without touching the drawing surface
hover_height = 5

# location and size of the playing surface
play_grid = {
    'center': {'x': 180, 'y': 0, 'z': paper_height},
    'square_size': 30
}

num_squares = 9
empty_mark = 0
user_mark = 1
uarm_mark = 2

# get region locations based on the grid location/size
# first is top-left, last is bottom-right
# also, remember the XY axis are reversed on the uArm :(
region_locations = [play_grid['center'].copy() for i in range(num_squares)]
region_locations[0]['y'] += play_grid['square_size']
region_locations[3]['y'] += play_grid['square_size']
region_locations[6]['y'] += play_grid['square_size']
region_locations[2]['y'] -= play_grid['square_size']
region_locations[5]['y'] -= play_grid['square_size']
region_locations[8]['y'] -= play_grid['square_size']
region_locations[0]['x'] += play_grid['square_size']
region_locations[1]['x'] += play_grid['square_size']
region_locations[2]['x'] += play_grid['square_size']
region_locations[6]['x'] -= play_grid['square_size']
region_locations[7]['x'] -= play_grid['square_size']
region_locations[8]['x'] -= play_grid['square_size']

print_output_format = '''
***********
{0}  | {1} |  {2}
-----------
{3}  | {4} |  {5}
-----------
{6}  | {7} |  {8}
***********'''

mark_to_char = {
    empty_mark: ' ',
    uarm_mark: 'x',
    user_mark: 'o'
}

winning_sequences = [
    (0, 1, 2), # top
    (0, 4, 8), # cross
    (0, 3, 6), # left
    (1, 4, 7), # center-vertical
    (2, 5, 8), # right
    (2, 4, 6), # cross
    (3, 4, 5), # center-horizontal
    (6, 7, 8)  # bottom
]


def find_paper_height(bot):
    bot.disable_all_motors()
    input('Press on paper then ENTER: ')
    bot.enable_all_motors()
    return bot.position['z'] - 0.5


def get_cross_coords(center, radius, angle=0):
    rad_offset = (angle / 360) * 2 * math.pi
    line_radians = [
        (0.75 * math.pi) + rad_offset, # top-left
        (1.75 * math.pi) + rad_offset, # bottom-right
        (0.25 * math.pi) + rad_offset, # top-right
        (1.25 * math.pi) + rad_offset  # bottom-left
    ]
    pen_down_points = []
    # add the first line
    for rad in line_radians:
        p = center.copy()
        p['x'] += radius * math.sin(rad)
        p['y'] += radius * math.cos(rad)
        p['drawing'] = True
        pen_down_points.append(p)
    # create a new list, to hold the line points plus hover points
    points = pen_down_points[:2]
     # lift up off the paper after the first lines and before second line
    for i in [1, 2]:
        hover = pen_down_points[i].copy()
        hover['z'] += hover_height
        hover['drawing'] = False
        points.append(hover)
    points += pen_down_points[2:]
    return points


def get_circle_coords(center, radius, line_length=3, start_rad=0, end_rad=None):
    two_pi = 2 * math.pi
    thresh_radian = two_pi
    if end_rad is not None:
        while end_rad <= 0:
            end_rad += two_pi
        thresh_radian = end_rad
    circum = radius * two_pi
    draw_length = circum * (thresh_radian / two_pi)
    radian_step = two_pi * (line_length / draw_length)
    curr_radian = start_rad
    points = []
    while curr_radian <= thresh_radian:
        p = center.copy()
        p['x'] += radius * math.sin(curr_radian)
        p['y'] += radius * math.cos(curr_radian)
        p['drawing'] = True
        points.append(p)
        curr_radian += radian_step
    return points


def get_line_coords(point_a, point_b):
    point_a = point_a.copy()
    point_b = point_b.copy()
    point_a['drawing'] = True
    point_b['drawing'] = True
    return [point_a, point_b]


def get_grid_coords(center, square_size):
    line_length = square_size * 3
    center_offset = square_size / 2

    top = center['y'] + (line_length / 2)
    bottom = center['y'] - (line_length / 2)
    left = center['x'] - (line_length / 2)
    right = center['x'] + (line_length / 2)

    touch_z = center['z']
    hover_z = center['z'] + hover_height

    points = [
        # line
        {'x': right, 'y': center['y'] + center_offset, 'z': touch_z, 'drawing': True},
        {'x': left, 'y': center['y'] + center_offset, 'z': touch_z, 'drawing': True},
        {'x': left, 'y': center['y'] + center_offset, 'z': hover_z}, # lift up
        # line
        {'x': right, 'y': center['y'] - center_offset, 'z': hover_z}, # move
        {'x': right, 'y': center['y'] - center_offset, 'z': touch_z, 'drawing': True},
        {'x': left, 'y': center['y'] - center_offset, 'z': touch_z, 'drawing': True},
        {'x': left, 'y': center['y'] - center_offset, 'z': hover_z}, # lift up
        # line
        {'x': center['x'] + center_offset, 'y': top, 'z': hover_z}, # move
        {'x': center['x'] + center_offset, 'y': top, 'z': touch_z, 'drawing': True},
        {'x': center['x'] + center_offset, 'y': bottom, 'z': touch_z, 'drawing': True},
        {'x': center['x'] + center_offset, 'y': bottom, 'z': hover_z}, # lift up
        # line
        {'x': center['x'] - center_offset, 'y': bottom, 'z': hover_z}, # move
        {'x': center['x'] - center_offset, 'y': bottom, 'z': touch_z, 'drawing': True},
        {'x': center['x'] - center_offset, 'y': top, 'z': touch_z, 'drawing': True}
    ]
    return points


def adjust_speed_during_drawing(bot, point, settings_pushed):
    if point.get('drawing'):
        if not settings_pushed:
            bot.push_settings()
            bot.speed(draw_speed)
            bot.acceleration(draw_accel)
        return True
    elif settings_pushed:
        bot.pop_settings()
    return False


def draw_shape(bot, points):
    hover_pos = {ax: points[0][ax] for ax in 'xyz'}
    hover_pos['z'] += hover_height
    bot.move_to(**hover_pos)
    settings_pushed = False
    for p in points:
        settings_pushed = adjust_speed_during_drawing(bot, p, settings_pushed)
        coord = {ax: p[ax] for ax in 'xyz'}
        bot.move_to(**coord)
    if settings_pushed:
        bot.pop_settings()
    hover_pos = {ax: points[-1][ax] for ax in 'xyz'}
    hover_pos['z'] += hover_height
    bot.move_to(**hover_pos)


def reset_uarm(bot):
    bot.speed(move_speed)
    bot.acceleration(move_accel)
    bot.rotate_to(wrist_centered_angle)


def setup_uarm():
    global paper_height
    bot = uarm_scan_and_connect()
    if input('Type any letter then ENTER to home: '):
        bot.home()
    reset_uarm(bot)
    return bot


def draw_playing_grid(bot):
    play_grid['center']['z'] = paper_height
    grid_points = get_grid_coords(
        play_grid['center'], play_grid['square_size'])
    draw_shape(bot, grid_points)


def get_number_mismatch(old_regions, new_regions):
    old_regions = [bool(v) for v in old_regions]
    if len(old_regions) != len(new_regions):
        raise RuntimeError(
            'Number old ({0}) doesnt match number new ({1})'.format(
                len(old_regions), len(new_regions)))
    mismatch_indexes = []
    for i in range(len(old_regions)):
        # only detect changes from False -> True
        if not old_regions[i] and new_regions[i]:
            mismatch_indexes.append(int(i))
    return len(mismatch_indexes)


def convert_camera_regions(old_regions, new_regions, empy_mark, user_mark):
    converted_regions = []
    for i, v in enumerate(old_regions):
        if new_regions[i]:
            if old_regions[i] != empy_mark:
                converted_regions.append(int(old_regions[i])) # copy old value
            else:
                converted_regions.append(user_mark) # user drew the mark
        else:
            converted_regions.append(empy_mark) # it's empty
    return converted_regions


def get_region_to_draw(regions):

    # sort by number of empty-markings
    def _get_mode_mark_of_seq_idx(seq_idxs):
        # return the mode of the region values
        # these should only have either two values, EMPTY or UARM/USER marking
        seq_vals = [regions[s_idx] for s_idx in seq_idxs]
        return max(seq_vals, key=seq_vals.count)


    def _reduce_to_winners_or_possible_winners(winner_seqs):
        has_winner = False
        winners_list = []
        if len(winner_seqs):
            for seq_idxs in winner_seqs:
                if _get_mode_mark_of_seq_idx(seq_idxs) != empty_mark:
                    has_winner = True
                    winners_list.append(seq_idxs)
        if has_winner:
            winner_seqs = winners_list
        random.shuffle(winner_seqs)  # randomized shuffle of indices
        return winner_seqs, has_winner


    def _get_empty_idx(seq_idxs):
        empty_idxs = []
        for idx in seq_idxs:
            if regions[idx] == empty_mark:
                empty_idxs.append(idx)
        if not len(empty_idxs):
            return None
        random.shuffle(empty_idxs)  # randomized shuffle of indices
        return empty_idxs[0]


    # loop through each uarm/user marked region
    uarm_winners = []
    user_winners = []
    for r_idx, val in enumerate(regions):
        for seq_idxs in winning_sequences:
            if r_idx == seq_idxs[0]:
                seq_vals = [regions[s_idx] for s_idx in seq_idxs]
                # get list of possible winning sequences
                if user_mark not in seq_vals:
                    uarm_winners.append(seq_idxs)
                if uarm_mark not in seq_vals:
                    user_winners.append(seq_idxs)

    uarm_winners, _ = _reduce_to_winners_or_possible_winners(uarm_winners)
    user_winners, user_has_winner = _reduce_to_winners_or_possible_winners(user_winners)

    if user_has_winner:
        # play defense
        return _get_empty_idx(user_winners[0])
    elif len(uarm_winners):
        # play offense
        return _get_empty_idx(uarm_winners[0])
    else:
        # no possible winner, pick randomly from empty regions
        return _get_empty_idx([i for i in range(num_squares)])


def draw_mark_on_region(bot, region_idx, mark):
    loc = region_locations[region_idx].copy()
    loc['z'] = paper_height
    coords = None
    mark_radius = play_grid['square_size'] * 0.25
    if mark.lower() == 'x':
        coords = get_cross_coords(loc, mark_radius)
    elif mark.lower() == 'o':
        coords = get_circle_coords(loc, mark_radius)
    else:
        raise RuntimeError('Unknown marking: {0}'.format(mark))
    draw_shape(bot, coords)


def draw_winning_line(bot, win_idxs):
    min_idx = min(win_idxs)
    max_idx = max(win_idxs)
    min_loc = region_locations[min_idx].copy()
    max_loc = region_locations[max_idx].copy()
    min_loc['z'] = paper_height
    max_loc['z'] = paper_height
    points = get_line_coords(min_loc, max_loc)
    draw_shape(bot, points)


def draw_face(bot, regions, happy):
    empty_idxs = [i for i, r in enumerate(regions) if r == empty_mark]
    face_loc = None
    if len(empty_idxs):
        random.shuffle(empty_idxs)
        face_loc = region_locations[empty_idxs[0]].copy()
    else:
        face_loc = region_locations[-2]
        face_loc['x'] -= play_grid['square_size']
    face_loc['z'] = paper_height

    face_radius = play_grid['square_size'] * 0.3
    eye_x_offset = face_radius * 0.3
    eye_y_offset = face_radius * 0.3
    eye_height = face_radius * 0.25
    mouth_radius = face_radius * 0.6

    circle_coords = get_circle_coords(face_loc, face_radius)
    draw_shape(bot, circle_coords)

    eye_left_center = face_loc.copy()
    eye_left_center['x'] -= eye_x_offset
    eye_left_center['y'] += eye_y_offset
    eye_left_top = eye_left_center.copy()
    eye_left_bottom = eye_left_center.copy()
    eye_left_top['x'] += (eye_height / 2)
    eye_left_bottom['x'] -= (eye_height / 2)
    eye_left_points = get_line_coords(eye_left_top, eye_left_bottom)
    draw_shape(bot, eye_left_points)

    eye_right_center = face_loc.copy()
    eye_right_center['x'] -= eye_x_offset
    eye_right_center['y'] -= eye_y_offset
    eye_right_top = eye_right_center.copy()
    eye_right_bottom = eye_right_center.copy()
    eye_right_top['x'] += (eye_height / 2)
    eye_right_bottom['x'] -= (eye_height / 2)
    eye_right_points = get_line_coords(eye_right_top, eye_right_bottom)
    draw_shape(bot, eye_right_points)

    mouth_center = face_loc.copy()
    if not happy:
        mouth_center['x'] += mouth_radius
    mouth_start = math.pi * 0
    mouth_end = math.pi * 1
    if not happy:
        mouth_start, mouth_end = mouth_end, mouth_start
    mouth_coords = get_circle_coords(
        mouth_center, mouth_radius, line_length=2,
        start_rad=mouth_start, end_rad=mouth_end)
    draw_shape(bot, mouth_coords)


def monitor_grid(bot):
    bot.move_to(**observer_pos)
    bot.rotate_to(wrist_centered_angle)
    bot.wait_for_arrival()


def are_regions_full(regions):
    for r in regions:
        if not r:
            return False
    return True


def are_regions_empty(regions):
    for r in regions:
        if r:
            return False
    return True


def get_winner_indices(regions):
    # go through each region
    for idx, m in enumerate(regions):
        # for the region, go through each sequence
        for seq in winning_sequences:
            # if the region matches the sequences first spot, test it
            if idx == seq[0] and m != empty_mark:
                # count all the matching regions in the sequence
                matches = sum([1 if regions[i] == m else 0 for i in seq])
                # if all the regions match, it's a winner
                if matches == len(seq):
                    return seq
    return None


def print_regions(regions):
    region_marks = [mark_to_char[v] for v in regions]
    print(print_output_format.format(*region_marks))


def run_cli_game():
    regions = [empty_mark for i in range(num_squares)]
    uarm_turn = True
    while True:
        if uarm_turn:
            bot_idx = get_region_to_draw(regions)
            regions[bot_idx] = uarm_mark
            uarm_turn = False
        else:
            input_msg = 'Enter index to draw a mark (0 - {0}): '
            res = input(input_msg.format(num_squares - 1))
            try:
                user_idx = int(res)
                regions[user_idx] = user_mark
                uarm_turn = True
            except Exception as e:
                print(e)
        print_regions(regions)
        win_idx = get_winner_indices(regions)
        if win_idx or are_regions_full(regions):
            if win_idx:
                m = mark_to_char[regions[win_idx[0]]]
                print('{0} is the winner! -> {1}'.format(m, win_idx))
            else:
                print('No winner, restarting game')
            regions = [empty_mark for i in range(num_squares)]
            uarm_turn = True


def auto_mode(bot, camera):

    def _wait_for_empty(state):
        print('Please start with an empty playing space. Waiting...')
        monitor_grid(bot)
        while not state['empty'] or state['moving']:
            time.sleep(0.5)
            state = camera.read_json()
        print('Thank you, playing space is now empty')


    def _test_and_react_to_end_game(regions, state):
        win_idx = get_winner_indices(regions)
        if win_idx or are_regions_full(regions):
            print('Game is over')
            if win_idx:
                win_mark = regions[win_idx[0]]
                print('{0} is the winner!'.format(mark_to_char[win_mark]))
                draw_winning_line(bot, win_idx)
                happy = (win_mark == uarm_mark)
                draw_face(bot, regions, happy)
            else:
                print('No winner!')
                draw_face(bot, regions, False)
            _wait_for_empty(state)
            return True
        return False


    game_state = {
        'regions': [empty_mark for i in range(num_squares)],
    }
    just_started = True
    while True:
        # move to the top each time, and get the state from the camera
        monitor_grid(bot)
        time.sleep(0.5)
        state = camera.read_json()

        # do nothing while there's movement
        if state['moving']:
            continue

        # nothing is drawn, so draw a grid
        if state['empty']:
            just_started = False
            draw_playing_grid(bot)
            game_state['regions'] = [empty_mark for i in range(num_squares)]
            # HACK: overwrite camera state, to force it to immediately
            #       start drawing it's first mark, without first rising up
            state['empty'] = False
            state['moving'] = True
            state['regions'] = [empty_mark for i in range(num_squares)]

        # make sure we're not starting with a previously started game
        total_drawn = sum([1 if v else 0 for v in state['regions']])
        if just_started:
            if total_drawn == 0:
                just_started = False
            else:
                _wait_for_empty(state)
            continue

        # wait for 1 region to not match, then assume it's a user's marking
        num_mismatch = get_number_mismatch(
            game_state['regions'], state['regions'])
        if num_mismatch == 0 and total_drawn > 0:
            continue
        elif num_mismatch > 1:
            print('Too many regions mismatch {0}'.format(num_mismatch))
            print('Current State');
            print(game_state['regions'])
            print('Camera State');
            print(state['regions'])
            continue

        # update regions from the camera
        game_state['regions'] = convert_camera_regions(
            game_state['regions'], state['regions'], empty_mark, user_mark)
        print_regions(game_state['regions'])

        # did the user just end the game?
        if _test_and_react_to_end_game(game_state['regions'], state):
            just_started = True
            continue

        # uarm makes it's move
        region_idx = get_region_to_draw(game_state['regions'])
        draw_mark_on_region(bot, region_idx, 'x')
        game_state['regions'][region_idx] = uarm_mark; # update regions
        print_regions(game_state['regions'])

        # did the uarm just end the game?
        if _test_and_react_to_end_game(game_state['regions'], state):
            just_started = True
            continue


def manual_mode(bot, camera):
    while True:
        monitor_grid(bot)
        msg = 'G (grid), H (home), R (read camera), XN (x-mark), ON (o-mark)'
        res = input(msg)
        if not res:
            continue
        cmd = res.lower()[0]
        idx = res.lower()[-1]
        if cmd == 'g':
            draw_playing_grid(bot)
        elif cmd == 'h':
            bot.home()
            reset_uarm(bot)
        elif cmd == 'r':
            print(camera.read_json())
        elif cmd == 'x' or cmd == 'o':
            try:
                idx = int(res.lower()[-1])
                draw_mark_on_region(bot, idx, cmd)
            except Exception as e:
                print(e)


if __name__ == "__main__":
    input_msg = 'Type any letter then ENTER to {0}: '
    if input(input_msg.format('simulate a game')):
        run_cli_game()
    camera = openmv_port.OpenMVPort()
    robot = setup_uarm()
    atexit.register(robot.sleep)
    if input(input_msg.format('find paper height')):
        paper_height = find_paper_height(robot)
        print('Paper height is: {0}'.format(paper_height))
        time.sleep(1) # wait a second for hand to move away from uArm
        monitor_grid(robot)
    elif input(input_msg.format('use auto-mode')):
        auto_mode(robot, camera)
    else:
        manual_mode(robot, camera)
