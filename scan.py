from control import Controller
import time

STEP = 5
DELAY = 0.5

ctl = Controller(1)

ctl.print_status()

for tilt in range(0,180,2*STEP):
    ctl.set_tilt(tilt)
    time.sleep(0.01)
    for pan in range(0,181,STEP):
        print(f"Pan: {pan}, tilt: {tilt}")
        ctl.set_pan(pan)
        time.sleep(DELAY)
    ctl.set_tilt(tilt+STEP)
    time.sleep(0.01)
    for pan in range(180,0,-STEP):
        print(f"Pan: {pan}, tilt: {tilt}")
        ctl.set_pan(pan)
        time.sleep(DELAY)

