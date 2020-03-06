import atexit
import json
import math
import sys
import time

import serial

# relative import
sys.path.append('../..')
from uarm_helpers import uarm_scan_and_connect

# Z position of where pen touches paper
# found through `find_paper_height()`
paper_height = 24

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


def find_camera_port():
    return '/dev/tty.usbmodem0000000000111'


def create_camera_port():
    port = serial.Serial()
    port.baudrate = 115200
    port.port = find_camera_port()
    port.timeout = 2
    return port


def open_camera_port(port):
    port.open()
    port.reset_input_buffer()


def close_camera_port(port):
    port.reset_input_buffer()
    port.close()


def read_camera_port(port, retries=3):
    while port.in_waiting:
        port.readline()
    data = port.readline()
    print(data)
    if data:
        try:
            return json.loads(data)
        except json.decoder.JSONDecodeError as e:
            print('Error parsing data from port')
            print(data)
            if retries == 0:
                raise e
    return read_camera_port(port, retries=retries - 1)


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


def get_circle_coords(center, radius, line_length=3):
    two_pi = 2 * math.pi
    circum = radius * two_pi
    radian_step = two_pi * (line_length / circum)
    curr_radian = 0
    points = []
    while curr_radian < two_pi:
        p = center.copy()
        p['x'] += radius * math.sin(curr_radian)
        p['y'] += radius * math.cos(curr_radian)
        p['drawing'] = True
        points.append(p)
        curr_radian += radian_step
    points.append(points[0].copy())
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
        {'x': left, 'y': center['y'] + center_offset, 'z': touch_z, 'drawing': True},
        {'x': right, 'y': center['y'] + center_offset, 'z': touch_z, 'drawing': True},
        {'x': right, 'y': center['y'] + center_offset, 'z': hover_z}, # lift up
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
            bot.speed(20)
            bot.acceleration(3)
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


def setup_uarm():
    global paper_height
    bot = uarm_scan_and_connect()
    bot.speed(100).acceleration(3).rotate_to(wrist_centered_angle)
    if input('Type any letter then ENTER to home: '):
        bot.home()
    if input('Type any letter then ENTER to find paper: '):
        paper_height = find_paper_height(bot)
        print('Paper height is: {0}'.format(paper_height))
        time.sleep(1)
    return bot


def draw_playing_grid(bot):
    play_grid['center']['z'] = paper_height
    grid_points = get_grid_coords(
        play_grid['center'], play_grid['square_size'])
    draw_shape(swift, grid_points)


def get_number_mismatch(old_regions, new_regions):
    old_regions = [bool(v) for v in old_regions]
    if len(old_regions) != len(new_regions):
        raise RuntimeError(
            'Number old ({0}) doesnt match number new ({1})'.format(
                len(old_regions), len(new_regions)))
    mismatch_indexes = []
    for i in range(len(old_regions)):
        if old_regions[i] != new_regions[i]:
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
    # TODO: randomize the square
    # TODO: make selection "smart"
    for i in range(len(regions)):
        if regions[i] == 0:
            return i


def draw_mark_on_region(bot, region_idx, mark):
    loc = region_locations[region_idx].copy()
    loc['z'] = paper_height
    coords = None
    if mark.lower() == 'x':
        coords = get_cross_coords(loc, play_grid['square_size'] / 2)
    elif mark.lower() == 'o':
        coords = get_circle_coords(loc, play_grid['square_size'] / 2)
    else:
        raise RuntimeError('Unknown marking: {0}'.format(mark))
    draw_shape(bot, coords)


def wait_for_instructions(swift, camera):
    open_camera_port(camera)
    game_state = {
        'regions': [empty_mark for i in range(num_squares)],
    }
    just_started = True
    while True:
        # move to the top each time, and get the state from the camera
        swift.move_to(**observer_pos).rotate_to(wrist_centered_angle)
        swift.wait_for_arrival()
        state = read_camera_port(camera)

        # do nothing while there's movement
        if state['moving']:
            continue

        # nothing is drawn, so draw a grid
        if state['empty']:
            just_started = False
            print('Drawing Grid')
            draw_playing_grid(swift)
            game_state['regions'] = [empty_mark for i in range(num_squares)]
            print('\n\n\n\n')
            continue

        # make sure we're not starting with a previously started game
        total_drawn = sum([1 if v else 0 for v in state['regions']])
        if total_drawn > 0 and just_started:
            print('Please start with an empty playing space. Waiting...')
            swift.move_to(**observer_pos).rotate_to(wrist_centered_angle)
            swift.wait_for_arrival()
            while not state['empty'] or state['moving']:
                state = read_camera_port(camera)
            print('Thank you, playing space is now empty')
            print('\n\n\n\n')
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
            print('\n\n\n\n')
            continue

        # get the next move to make, and draw a mark in that region
        game_state['regions'] = convert_camera_regions(
            game_state['regions'], state['regions'], empty_mark, user_mark)
        region_idx = get_region_to_draw(game_state['regions'])
        draw_mark_on_region(swift, region_idx, 'x')
        game_state['regions'][region_idx] = uarm_mark;
        print('\n\n\n\n')


camera = create_camera_port()
swift = setup_uarm()
atexit.register(swift.sleep)

if input('Press any key to enter camera monitor mode'):
    swift.move_to(**observer_pos).rotate_to(wrist_centered_angle)
    swift.wait_for_arrival()
    while True:
        pass

wait_for_instructions(swift, camera)
