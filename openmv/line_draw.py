import sensor

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE) # grayscale is faster
sensor.set_framesize(sensor.QQVGA)
sensor.skip_frames(time = 2000)

max_lines = 20

def get_lines(img):
    return img.find_line_segments(merge_distance=2, max_theta_diff=5)


def sort_lines(lines):
    return sorted(lines, key=lambda l: l.length(), reverse=True)


def clear_image(img, color=255):
    img.draw_rectangle(0, 0, img.width(), img.height(), color=color, fill=True)


def draw_lines(img, lines, color=0):
    for l in lines:
        img.draw_line(l.line(), color=color)


while(True):
    img = sensor.snapshot()
    lines = get_lines(img)
    lines = sort_lines(lines)[:max_lines]
    clear_image(img)
    draw_lines(img, lines)
