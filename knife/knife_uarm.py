import atexit
import sys
import time

from uarm import uarm_create, uarm_scan_and_connect

sys.path.append('..')
from utils import openmv_port

wrist_centered_angle = 100

move_speed = 600
move_acceleration = 20

knife_height = 19
hover_height = knife_height + 25
middle_knuckle = {'x': 200, 'y': 10, 'z': knife_height + 150}
finger_coords = [
    {'x': 195, 'y': -58, 'z': knife_height},
    {'x': 158, 'y': -37, 'z': knife_height},
    {'x': 135, 'y': -12, 'z': knife_height},
    {'x': 137, 'y': 22, 'z': knife_height},
    {'x': 166, 'y': 60, 'z': knife_height},
    {'x': 212, 'y': 94, 'z': knife_height}
]


def move_to_finger_coordinate(bot, pos):
    hover_now = robot.position
    hover_now['z'] = max(hover_now['z'], hover_height, pos['z'])
    hover_target = pos.copy()
    hover_target['z'] = hover_now['z']
    robot.move_to(**hover_now).move_to(**hover_target).move_to(**pos)


if __name__ == "__main__":

    robot = uarm_scan_and_connect()
    atexit.register(robot.sleep)

    robot.rotate_to(wrist_centered_angle)

    input_msg = 'Type any letter then ENTER to {0}: '

    if input(input_msg.format('home')):
        robot.home()
    if input(input_msg.format('read coordinates')):
        robot.disable_all_motors()
        while True:
            robot.update_position()
            print(robot.position)
    if input(input_msg.format('test fingers')):
        while True:
            res = input('Enter finger number, or M for middle:')
            if not res:
                continue
            if res.lower() == 'm':
                move_to_finger_coordinate(robot, middle_knuckle)
                continue
            if res.lower() == 'a':
                robot.push_settings()
                robot.speed(100).acceleration(1)
                robot.push_settings()
                move_to_finger_coordinate(robot, middle_knuckle)
                input('Ready?')
                move_to_finger_coordinate(robot, finger_coords[0])
                robot.wait_for_arrival()
                time.sleep(2)
                robot.speed(move_speed).acceleration(move_acceleration)
                for i in range(1, len(finger_coords)):
                    move_to_finger_coordinate(robot, finger_coords[i])
                for i in range(len(finger_coords) - 2, -1, -1):
                    move_to_finger_coordinate(robot, finger_coords[i])
                time.sleep(3)
                robot.pop_settings()
                move_to_finger_coordinate(robot, middle_knuckle)
                robot.pop_settings()
                continue
            else:
                try:
                    idx = int(res)
                    pos = finger_coords[idx].copy()
                    move_to_finger_coordinate(robot, pos)
                    continue
                except Exception as e:
                    print(e)
