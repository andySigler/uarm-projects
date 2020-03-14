import sensor, math, json

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time = 2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
sensor.set_auto_exposure(False)

# combine w/ `img.rotation_corr(z_rotation=90)`
w_x_offset = int((sensor.width() - sensor.height()) / 2)
sensor.set_windowing((w_x_offset, 0, sensor.height(), sensor.height()))
sensor.set_hmirror(True)

# update using "Tools->Machine Vision->Threshold Editor"
blob_color_thresh = [(31, 100, 21, 127, 22, 127)]

w = sensor.width()
square_size_min = int(w * 0.125)                # min size of square
square_size_max = int(w * 0.75)                  # max size of square
area_thresh = square_size_min * square_size_min # min size of bounding box
pix_thresh = int(area_thresh * 0.25)            # min number of pixels

movement_thresh = w * 0.015         # max number of pixels before it's considerate to have moved
still_frames_count = 0              # keep count of number of "still" readings
still_frames_thresh = 20            # this many "still" readings means it's really still
prev_blob = []


def get_max_movement(prev_blobs, new_blob):
    max_movement = 0
    for b in prev_blobs:
        x_diff = b.cx() - new_blob.cx()
        y_diff = b.cy() - new_blob.cy()
        movement = math.sqrt(math.pow(x_diff, 2) + math.pow(y_diff, 2))
        if movement > max_movement:
            max_movement = movement
    return max_movement


while(True):
    img = sensor.snapshot()
    img.lens_corr(1.8)
    img.rotation_corr(z_rotation=90)
    blobs = img.find_blobs(
        blob_color_thresh,
        pixels_threshold=pix_thresh,
        area_threshold=area_thresh,
        merge=False)
    square_blob = None
    for b in blobs:
        square_thresh = int(b.w() * 0.2)
        is_square = abs(b.h() - b.w()) < square_thresh
        is_right_size = b.w() > square_size_min and b.w() < square_size_max
        if is_square and is_right_size:
            square_blob = b
    data = {
        'empty': True,
        'position': {'x': 0, 'y': 0},
        'moving': False
    }
    if square_blob:
        img.draw_rectangle(square_blob.rect())
        data['empty'] = False
        # convert to relative position (0.0-1.0)
        data['position']['x'] = round(float(square_blob.cx() / img.width()), 2)
        data['position']['y'] = round(float(square_blob.cy() / img.height()), 2)
        data['moving'] = True
        movement = get_max_movement(prev_blob, square_blob)
        if abs(movement) < movement_thresh:
            data['moving'] = False
        prev_blob.append(square_blob)
        if len(prev_blob) > still_frames_thresh:
            start_idx = len(prev_blob) - still_frames_thresh
            prev_blob = prev_blob[start_idx:]
    data_str = json.dumps(data)
    print(data_str)


