import math
import time

from uarm_helpers import uarm_scan_and_connect

paper_height = 11  # found through `find_paper_height()`


def find_paper_height(bot):
    bot.disable_all_motors()
    input('Press on paper then ENTER: ')
    bot.enable_all_motors()
    return bot.position['z']


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
        points.append(p)
        curr_radian += radian_step
    points.append(points[0].copy())
    return points


def draw_circle(bot, points):
    hover_pos = points[0].copy()
    hover_pos['z'] += 5
    bot.move_to(**hover_pos)
    bot.push_settings()
    bot.speed(20).acceleration(3)
    for p in points:
        bot.move_to(**p)
    bot.pop_settings()
    bot.move_to(**hover_pos)


swift = uarm_scan_and_connect()
swift.speed(100).acceleration(10)

if input('Type any letter then ENTER to home: '):
    swift.home()
if input('Type any letter then ENTER to find paper: '):
    paper_height = find_paper_height(swift)
    print('Paper height is: {0}'.format(paper_height))
    time.sleep(1)

circle_center = {'x': 150, 'y': -20, 'z': paper_height}
circle_points = get_circle_coords(circle_center, 10)
draw_circle(swift, circle_points)

swift.sleep()
