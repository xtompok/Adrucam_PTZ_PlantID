#!/usr/bin/env python

from autofocus import sobel, laplacian, laplacian2
from control import Controller
from capture import gstreamer_pipeline
import time
import cv2


def main():
    ctl = Controller(1)
    ctl.print_status()

    cam = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)

    z = float(input("Zoom: "))
    f = float(input("Focus: "))  
    while True:
        ctl.set_zoom(z)
        ctl.set_focus(f)
        ctl.waiting_for_free()
        time.sleep(0.1)
#        for _ in range(12):
#            ret,frame = cam.read()
        print("-----")
        for _ in range(2):
            ret,frame = cam.read()
            cv2.imshow("Camera", frame)
            print(f"Z: {z}, F: {f}, sobel: {sobel(frame)}, laplacian: {laplacian(frame)}, laplacian2: {laplacian2(frame)}")
        key = cv2.waitKey()
        if key == 81:
            f -= 0.01
        if key == 83:
            f += 0.01

    cv2.destroyWindow(self.window_name)



if __name__ == '__main__':
    main()
