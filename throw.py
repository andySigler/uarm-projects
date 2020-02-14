import math
import time

from uarm_helpers import uarm_scan_and_connect


ball_pos = {'x': 117, 'y': -64, 'z': 50}
thow_spec = {
    'start': {'x': 120, 'y': -240, 'z': 45},
    'end': {'x': 120, 'y': 240, 'z': 150},
    'speed': 600,
    'acceleration': 30,
    'delay': 0.3
}


def find_ball_pos(bot):
    bot.disable_all_motors()
    input('Press on ball then ENTER: ')
    bot.enable_all_motors()
    return bot.position


def pick_up_ball(bot, pos):
    hover_pos = pos.copy()
    hover_pos['z'] += 40
    bot.move_to(**hover_pos)
    bot.move_to(**pos).wait_for_arrival()
    bot.pump(True)
    bot.move_to(**hover_pos)


def throw_ball(bot, spec):
    bot.move_to(**spec['start']).wait_for_arrival()
    time.sleep(0.3)
    bot.speed(spec['speed']).acceleration(spec['acceleration'])
    bot.move_to(**spec['end'])
    time.sleep(spec['delay'])
    bot.pump(False)


swift = uarm_scan_and_connect();

if input('Type any letter then ENTER to home: '):
    swift.home()
if input('Type any letter then ENTER to find ball: '):
    ball_pos = find_ball_pos(swift)
    print('Ball pos is: {0}'.format(ball_pos))
    time.sleep(1)
pick_up_ball(swift, ball_pos)
throw_ball(swift, thow_spec)

swift.sleep()
