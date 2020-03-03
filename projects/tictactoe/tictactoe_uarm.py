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
paper_height = 20

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


def read_camera_port(port):
    port.reset_input_buffer()
    data = port.readline()
    if data:
        return json.loads(data)
    return None


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


def wait_for_instructions(swift, camera):
    swift.move_to(**observer_pos).rotate_to(wrist_centered_angle)
    open_camera_port(camera)
    while True:
        '''
        Read camera to determine:

            1) what squares have dark marks inside them
            2) when there is movement
            3) when the game state has updated since last move

        Using data from above:

            1) when to make next move
            2) what the next move is
            3) center coordinate for the next move

        Send instructions to uArm, either:

            1) draw an X or O at specified coordinate
            2) draw a finishing line from one coordinate to another
        '''
        pass


camera = create_camera_port()
swift = setup_uarm()
atexit.register(swift.sleep)

wait_for_instructions(swift, camera)
