#!/bin/sh

#gst-launch-1.0 nvarguscamerasrc aelock=true wbmode=0  exposuretimerange='1300000 1300000'  ! 'video/x-raw(memory:NVMM), width=4032, height=3040, framerate=10/1' ! nvvidconv ! videocrop left=1500 right=1500 top=1000 bottom=1000 ! omxh264enc !  h264parse ! rtph264pay config-interval=1 pt=96 ! gdppay ! tcpserversink host=0.0.0.0 port=9090
gst-launch-1.0 nvarguscamerasrc wbmode=0  ! 'video/x-raw(memory:NVMM), width=4032, height=3040, framerate=10/1' ! nvvidconv ! videocrop left=1500 right=1500 top=1000 bottom=1000 ! omxh264enc !  h264parse ! rtph264pay config-interval=1 pt=96 ! gdppay ! tcpserversink host=0.0.0.0 port=9090

