from uarm_helpers import uarm_scan_and_connect

swift = uarm_scan_and_connect(verbose=True);
swift.home()

swift.move_relative(x=50).move_relative(z=100)
swift.move_relative(y=-100).move_relative(y=200).move_relative(y=-100)
swift.rotate_to(angle=20).rotate_relative(angle=100)

swift.home().wait_for_arrival().disable_all_motors()
