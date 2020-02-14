import time

from uarm_helpers import uarm_scan_and_connect


def find_ball_pos(bot):
    bot.disable_all_motors()
    res = input('Press on ball, type "y" then ENTER: ')
    if res[0] != 'y':
        exit()
    bot.enable_all_motors()
    return bot.position


def pick_up_ball(bot, pos):
    hover_pos = pos.copy()
    hover_pos['z'] += 40
    bot.speed(100)
    bot.move_to(**hover_pos)
    bot.speed(40)
    bot.move_to(**pos).wait_for_arrival()
    bot.pump(True)
    bot.move_to(**hover_pos).wait_for_arrival()


def throw_ball(bot, start, end):
    bot.move_to(**start).wait_for_arrival()
    bot.speed(250)
    bot.acceleration(10)
    bot.move_to(**end)
    time.sleep(0.4)
    bot.pump(False)


# start and end throwing coordinates
ball_pos = {'x': 185, 'y': 5, 'z': 55}
throw_start = {'x': 190, 'y': 240, 'z': 45}
throw_end = {'x': 190, 'y': -240, 'z': 150}

swift = uarm_scan_and_connect();

res = input('Type \"y\" then ENTER to home: ')
if len(res) and res[0] == 'y':
    swift.home().wait_for_arrival()

res = input('Type \"y\" then ENTER to find ball: ')
if len(res) and res[0] == 'y':
    ball_pos = find_ball_pos(swift)
pick_up_ball(swift, ball_pos)
throw_ball(swift, throw_start, throw_end)

# finally home and rest
swift.home().wait_for_arrival().disable_all_motors()
