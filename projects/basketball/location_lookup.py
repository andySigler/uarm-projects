import math
import os


def generate(bot, camera, filename):
    cam_pos = None
    ball_pos = None
    file_line = '{0}, {1}, {2}, {3}, {4}\n'
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write(file_line.format(
                'OpenMV X', 'OpenMV Y', 'uArm X', 'uArm Y', 'uArm Z'))
    bot.move_to(**observer_pos).wait_for_arrival()
    while True:
        # move to the top
        res = input('c=CAM, b=BALL, s=SAVE, x=EXIT')
        if res == 'x':
            bot.move_to(**observer_pos).wait_for_arrival()
            return
        if res == 'c':
            data = camera.read_json()
            print(data)
            cam_pos = data['position']
            continue
        if res == 'b':
            bot.disable_all_motors()
            continue
        if res == 's':
            bot.update_position()
            bot.update_position()
            ball_pos = bot.position
            if cam_pos:
                with open(filename, 'a+') as f:
                    f.write(file_line.format(
                        cam_pos['x'],
                        cam_pos['y'],
                        ball_pos['x'],
                        ball_pos['y'],
                        ball_pos['z']))
            cam_pos = None
            ball_pos = None
            bot.move_to(**observer_pos).wait_for_arrival()
            continue


def load(filename):
    if not os.path.exists(filename):
        raise RuntimeError('No file found for: {0}'.format(filename))
    location_lookup = []
    with open(filename, 'r') as f:
        # OpenMV X, OpenMV Y, uArm X, uArm Y, uArm Z
        f.readline() # ignore the first line
        for line in f.readlines():
            line = line.strip()
            line_list = line.split(',')
            openmv = line_list[:2]
            uarm = line_list[2:]
            location_lookup.append({
                'openmv': {
                    'x': float(openmv[0]),
                    'y': float(openmv[1])
                },
                'uarm': {
                    'x': float(uarm[0]),
                    'y': float(uarm[1]),
                    'z': float(uarm[2])
                },
            })
    return location_lookup


def convert(cam_pos, lookup_table):
    # sort by nearest coordinates

    def sort_by_distance(d):
        pos = d['openmv']
        x_diff = cam_pos['x'] - pos['x']
        y_diff = cam_pos['y'] - pos['y']
        return math.sqrt(math.pow(x_diff, 2) + math.pow(y_diff, 2))

    lookup_table = [
        {
            k: v.copy()
            for k, v in d.items()
        }
        for d in lookup_table
    ]
    lookup_table.sort(key=sort_by_distance)
    # using closest neighbors, convert openmv to uarm millimeters
    a = lookup_table[0].copy()
    scaler_x = 0
    scaler_y = 0
    count = 0
    for i in range(1, 10):
        b = lookup_table[i].copy()
        openmv_diff_x = b['openmv']['x'] - a['openmv']['x']
        if openmv_diff_x == 0:
            continue
        openmv_diff_y = b['openmv']['y'] - a['openmv']['y']
        if openmv_diff_y == 0:
            continue
        uarm_diff_x = b['uarm']['x'] - a['uarm']['x']
        uarm_diff_y = b['uarm']['y'] - a['uarm']['y']
        scaler_x += uarm_diff_x / openmv_diff_x
        scaler_y += uarm_diff_y / openmv_diff_y
        count += 1
    scaler_x = scaler_x / count
    scaler_y = scaler_y / count
    # using millimeter conversion, and openmv offset, get uarm position
    openmv_offset_x = cam_pos['x'] - a['openmv']['x']
    openmv_offset_y = cam_pos['y'] - a['openmv']['y']
    uarm_offset_x = openmv_offset_x * scaler_x
    uarm_offset_y = openmv_offset_y * scaler_y
    real_pos = a['uarm'].copy()
    real_pos['x'] += uarm_offset_x
    real_pos['y'] += uarm_offset_y
    return real_pos
