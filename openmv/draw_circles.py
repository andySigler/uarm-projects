import sensor

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE) # grayscale is faster
sensor.set_framesize(sensor.QQVGA)
sensor.set_contrast(3)
sensor.skip_frames(time = 2000)

xy_margin = 20

while(True):
    img = sensor.snapshot()
    img.binary([(127, 255)])
    circles = img.find_circles(
        threshold=4000,
        x_margin=xy_margin,
        y_margin=xy_margin,
        r_margin=50,
        r_min=5,
        r_max=20,
        r_step=5
    )
    #img.draw_rectangle(0, 0, img.width(), img.height(), color=255, fill=True)
    for c in circles:
        img.draw_circle(c.x(), c.y(), c.r(), color=0)
