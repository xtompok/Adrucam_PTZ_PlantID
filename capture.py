#!/usr/bin/python3

import cv2
import time

def gstreamer_pipeline(
    capture_width=4032,
    capture_height=3040,
    cut_width=1000,
    cut_height=1000,
    framerate=10,
    flip_method=0,
):
    left = (capture_width-cut_width)/2
    right = left
    top = (capture_height-cut_height)/2
    bottom = top
    return (
        "nvarguscamerasrc wbmode=0  ! "
        #"nvarguscamerasrc aelock=true wbmode=0 exposuretimerange=\"33330 33330\" ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "videocrop left=%d right=%d top=%d bottom=%d !"
        "video/x-raw format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink max-buffers=1 drop=true"
        % (
            capture_width,
            capture_height,
            framerate,
            flip_method,
            left, right, top, bottom
        )
    )

def open_camera():
    cam = cv2.VideoCapture(gstreamer_pipeline(flip_method=0), cv2.CAP_GSTREAMER)
    return cam


def main():
    #cap = cv2.VideoCapture(" nvarguscamerasrc aelock=true wbmode=0  exposuretimerange='130000 130000'  ! 'video/x-raw(memory:NVMM), width=4032, height=3040, framerate=10/1' ! nvvidconv ! videocrop left=1500 right=1500 top=1000 bottom=1000 ! nvvidconv  ! video/x-raw, format=I420, appsink max-buffers=1 drop=true", cv2.CAP_GSTREAMER)
    cap = open_camera()
    print(gstreamer_pipeline(flip_method=0))
    #cap = cv2.VideoCapture("nvarguscamerasrc aelock=true wbmode=0 ! video/x-raw(memory:NVMM), width=4032, height=3040, format=(string)NV12, framerate=10/1 ! nvvidconv flip_method=0 ! videocrop left=1500 right=1500 top=1000 bottom=1000 ! video/x-raw format=(string)BGRx ! videoconvert ! video/x-raw, format=(string)BGR ! appsink", cv2.CAP_GSTREAMER)

    print("Capture object created")


    while True:
        ret, frame = cap.read()


        print(ret,len(frame),len(frame[0]))

        cv2.imwrite(f"{int(time.time())}.jpg",frame)
        time.sleep(1)

    cap.release()


if __name__ == '__main__':
    main()
