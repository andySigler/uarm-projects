import json

import sensor

sensor.reset()

sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA) # 320x240
sensor.skip_frames(time=2000)

sensor.set_contrast(3)
sensor.set_brightness(3)
sensor.set_gainceiling(128)
sensor.set_saturation(-3)

sensor.set_auto_exposure(True)
sensor.set_auto_whitebal(True)


def get_crop_coords(img):
    crop_percentage_x = 0.2
    crop_percentage_y = 0.15
    coords = {
        'x': int(img.width() * crop_percentage_x),
        'y': int(img.height() * crop_percentage_y)
    }
    coords['w'] = img.width() - (coords['x'] * 2)
    coords['h'] = img.height() - (coords['y'] * 2)
    return coords


def crop_image(img):
    coords = get_crop_coords(img)
    img.crop(
        roi=(coords['x'], coords['y'], coords['w'], coords['h']),
        copy_to_fb=True
    )
    return img;


def read_image():
    img = sensor.snapshot()
    img.lens_corr(1.8)
    img = crop_image(img)
    stats = img.get_statistics(threshold=[(0, 255)])
    hist = img.get_histogram()
    return (img, stats, hist)


def auto_binary(img):
    value = img.get_histogram().get_threshold().value()
    img.binary([(0, value)], invert=True)
    return img


def is_image_empty(stats, min_thresh=100):
    return stats.min() > min_thresh


def is_image_moving(stats, prev_stats, hist, count):
    is_moving = False
    if prev_stats is None:
        is_moving = True
    else:
        mean_diff = abs(stats.mean() - prev_stats.mean())
        min_diff = abs(stats.min() - prev_stats.min())
        med_diff = abs(stats.median() - prev_stats.median())
        stdev_diff = abs(stats.stdev() - prev_stats.stdev())
        if max([mean_diff, min_diff, med_diff, stdev_diff]) > 3:
            is_moving = True
    if not is_moving:
        perc_low = hist.get_percentile(0.25).value()
        perc_high = hist.get_percentile(0.95).value()
        if perc_high - perc_low > 30:
            is_moving = True;
    if not is_moving:
        count += 1
        if count < 10:
            is_moving = True
        return is_moving, count
    else:
        return True, 0


def get_region_offsets(img):
    w = img.width()
    h = img.height()
    s = [0.0125, 0.025, 0.05, 0.075]
    xy_offsets = [{'x': 0, 'y': 0} for i in range(9)]
    xy_offsets[0] = {'x': w * s[1], 'y': h * s[1]}      # top-left
    xy_offsets[1] = {'x': 0, 'y': h * -s[0]}            # top-center
    xy_offsets[2] = {'x': w * -s[1], 'y': h * s[1]}     # top-right
    xy_offsets[3] = {'x': w * s[1], 'y': h * -s[0]}     # center-left
    xy_offsets[4] = {'x': 0, 'y': h * -s[2]}            # center
    xy_offsets[5] = {'x': w * -s[1], 'y': h * -s[0]}    # center-right
    xy_offsets[6] = {'x': w * s[1], 'y': h * -s[1]}     # bottom-left
    xy_offsets[7] = {'x': 0, 'y': h * -s[3]}            # bottom-center
    xy_offsets[8] = {'x': w * -s[1], 'y': h * -s[1]}    # bottom-right
    return xy_offsets


def get_region_coords(img):
    width = img.width()
    height = img.height()
    region_size = (width / 3) * 0.5
    w = int(region_size)
    h = int(region_size)
    rel_offsets = [1 / 6, 1 / 2, 5 / 6]
    xy_offsets = get_region_offsets(img)
    regions = []
    for rel_y in rel_offsets:
        for rel_x in rel_offsets:
            offset = xy_offsets[len(regions)]
            offset_x = offset['x']
            offset_y = offset['y']
            center_x = (rel_x * width) + offset_x
            center_y = (rel_y * height) + offset_y
            x = int(center_x - (region_size / 2))
            y = int(center_y - (region_size / 2))
            regions.append({
                'x': x,
                'y': y,
                'w': int(region_size),
                'h': int(region_size),
                'roi': (x, y, w, h),
                'index': len(regions)
            })
    return regions


def get_regions(img, mean_thresh=240):
    region_coords = get_region_coords(img)
    stats = []
    for c in region_coords:
        s = img.get_statistics(threshold=[(0, 255)], roi=c['roi'])
        is_filled = s.min() == 0 and s.mean() < mean_thresh
        stats.append({
            'region': c,
            'filled': is_filled
        })
    return stats


def draw_regions(img, reg_stats):
    for stat in reg_stats:
        r = stat['region']
        fill_color = 220
        text_color = 20
        if stat['filled']:
            fill_color = 20
            text_color = 220
        img.draw_rectangle(r['x'], r['y'], r['w'], r['h'], color=fill_color, fill=True)
        img.draw_string(
            int(r['x'] + r['w'] / 10),
            int(r['y'] + r['h'] / 10),
            str(r['index']),
            scale=3,
            color=text_color
        )


def print_state(is_empty, is_moving, reg_stats):
    json_data = {
        'empty': is_empty,
        'moving': is_moving,
        'regions': []
    }
    if reg_stats and len(reg_stats):
        json_data['regions'] = [
            r['filled']
            for r in reg_stats
        ]
    json_str = json.dumps(json_data)
    print(json_str)


prev_stats = None
still_count = 0
while(True):
    img, stats, hist = read_image()
    is_empty = is_image_empty(stats)
    is_moving, still_count = is_image_moving(stats, prev_stats, hist, still_count)
    prev_stats = stats
    prev_hist = hist
    reg_stats = []
    if not is_empty and not is_moving:
        img = auto_binary(img)
        reg_stats = get_regions(img)
        draw_regions(img, reg_stats)
    print_state(is_empty, is_moving, reg_stats)
















