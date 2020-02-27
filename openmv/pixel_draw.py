import sensor

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_contrast(3)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time = 2000)

count = {
    'x': 32,
    'y': 24
}
total_points = count['x'] * count['y']
points_per_sec = 3
total_seconds = int(total_points / points_per_sec)
print('{0} total points ({1} seconds)'.format(total_points, total_seconds))
step = {
    'x': int(sensor.width() / count['x']),
    'y': int(sensor.height() / count['y'])
}
locations = [
    {'x': x * step['x'], 'y': y * step['y']}
    for x in range(count['x'])
    for y in range(count['y'])
]

while(True):
    img = sensor.snapshot()
    colors = [
        img.get_pixel(l['x'], l['y'])
        for l in locations
    ]
    for l, c in zip(locations, colors):
        drawn_c = 0
        if c > 127:
            drawn_c = 255
        img.draw_rectangle(l['x'], l['y'], step['x'], step['y'], color=drawn_c, fill=True)
