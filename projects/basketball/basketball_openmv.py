import sensor, math, json

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time = 2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

# update using "Tools->Machine Vision->Threshold Editor"
blob_color_thresh = [(14, 65, 28, 91, 1, 79)]

w = sensor.width()
square_thresh = int(w * 0.03125)                # max pixel diff b/w width/height
square_size_min = int(w * 0.125)                # min size of square
square_size_max = int(w * 0.1875)               # max size of square
area_thresh = square_size_min * square_size_min # min size of bounding box
pix_thresh = int(area_thresh * 0.25)            # min number of pixels

movement_thresh = w * 0.015         # max number of pixels before it's considerate to have moved
still_frames_count = 0              # keep count of number of "still" readings
still_frames_thresh = 10            # this many "still" readings means it's really still
prev_blob = None

while(True):
    img = sensor.snapshot().lens_corr(1.8)
    blobs = img.find_blobs(
        blob_color_thresh,
        pixels_threshold=pix_thresh,
        area_threshold=area_thresh,
        merge=False)
    square_blob = None
    for b in blobs:
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
        if prev_blob:
            x_diff = prev_blob.cx() - square_blob.cx()
            y_diff = prev_blob.cy() - square_blob.cy()
            movement = math.sqrt(math.pow(x_diff, 2) + math.pow(y_diff, 2))
            # test if it's moved too many pixels from previous reading
            if abs(movement) < movement_thresh:
                still_frames_count += 1
                # test if it's been still for enough sequential readings
                if still_frames_count > still_frames_thresh:
                    still_frames_count = still_frames_thresh
                    data['moving'] = False
            else:
                still_frames_count = 0
        else:
            still_frames_count = 0
    else:
        still_frames_count = 0
    prev_blob = square_blob
    data_str = json.dumps(data)
    print(data_str)


