import atexit
import math
import time

from uarm import uarm_create, uarm_scan_and_connect


def find_ball_pos(bot):
    bot.disable_all_motors()
    input('Press on ball then ENTER: ')
    bot.enable_all_motors()
    return bot.position


def pick_up_ball(bot, pos):
    bot.push_settings()
    bot.speed(100)
    hover_pos = pos.copy()
    hover_pos['z'] += 40
    bot.move_to(**hover_pos)
    bot.move_to(**pos).wait_for_arrival()
    bot.pump(True) # pick up
    bot.move_to(**hover_pos)
    bot.pop_settings()


def throw_ball(bot, spec):
    bot.push_settings()
    bot.speed(50)
    bot.move_to(**spec['start']).wait_for_arrival()
    time.sleep(0.3) # pause before throw
    bot.speed(spec['speed']).acceleration(spec['acceleration'])
    bot.move_to(**spec['end'])
    time.sleep(spec['delay']) # pause before release
    bot.pump(False) # release
    bot.pop_settings()


'''
Overview:

1) uarm scans for ball with camera
    - [OpenMV] find orange blob
    - [OpenMV] print blob coordinate
    {
        "empty": true,
        "moving": false,
        "position": {
            "y": 0,
            "x": 0
        }
    }
    - wait for blob to slow

2) uarm picks up ball
    - convert blob locaton to uarm location
    - hover over and pick up
    - move up and test the blob is gone

3) uarm throws ball
    - do some cool movements
    - throw ball at hoop
    - "dunk" on the hoop

'''


if __name__ == "__main__":

    # position where the camera can observe the entire drawing surface
    observer_pos = {'x': 145, 'y': 0, 'z': 140}
    ball_height = 23 # touches around 28, presses hard around 20
    visible_corners = [
        {'x': 111, 'y': -111, 'z': 0},  # top-left
        {'x': 126, 'y': 102, 'z': 0},   # top-right
        {'x': 270, 'y': -106, 'z': 0},  # bottom-left
        {'x': 271, 'y': -93, 'z': 0}    # bottom-right
    ]

    ball_pos = {'x': 117, 'y': -64, 'z': ball_height} # found w/ `find_ball_pos()`
    thow_spec = {
        'start': {'x': 130, 'y': -140, 'z': ball_pos['z'] + 5},
        'end': {'x': 130, 'y': 140, 'z': 145},
        'speed': 600,
        'acceleration': 30,
        'delay': 0.3
    }

    swift = uarm_scan_and_connect();
    # swift = uarm_create(simulate=True);
    atexit.register(swift.sleep)

    input_msg = 'Type any letter then ENTER to {0}: '

    if input(input_msg.format('home')):
        swift.home()

    if input(input_msg.format('observe')):
        swift.move_to(**observer_pos).wait_for_arrival().disable_base()

    if input(input_msg.format('print location')):
        swift.home().disable_all_motors()
        while True:
            swift.update_position()
            print(swift.position)
            time.sleep(0.05)

    if input(input_msg.format('find ball')):
        ball_pos = find_ball_pos(swift)
        thow_spec['start']['z'] = ball_pos['z'] + 5
        print('Ball pos is: {0}'.format(ball_pos))

    if input(input_msg.format('pickup and throw')):
        pick_up_ball(swift, ball_pos)
        throw_ball(swift, thow_spec)

    swift.sleep()
