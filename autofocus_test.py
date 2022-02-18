#!/usr/bin/env python

from autofocus import sobel, laplacian, laplacian2
from control import Controller
from capture import gstreamer_pipeline
import time
import cv2


def find_peak(vals,nsteps):
    bestup = None
    bestdown = None
    bestidx = None

    memratio = vals[0]/vals[1]
    for idx,val in enumerate(vals[2:]):
        ratio = vals[idx+1]/val
        if memratio < 1 and ratio > 1:
            if not bestidx:
                bestup = memratio
                bestdown = ratio
                bestidx = idx+1
            else:
                if ratio > bestdown:
                    bestup = memratio
                    bestdown = ratio
                    bestidx = idx+1
        memratio = ratio
    return (bestidx)/nsteps

def fine_focus_recursive(ctl,cam,minfocus,maxfocus,mindiff=0.01):
    if (maxfocus-minfocus < mindiff):
        return

    step = max((maxfocus-minfocus)/10,0.005)

    focus1 = max((minfocus+maxfocus)/2-step/2,0)
    focus2 = min((minfocus+maxfocus)/2+step/2,1)
    
    ret,frame = get_frame_focus(ctl,cam,focus1)
    laplac1 = laplacian2(frame)
    ret,frame = get_frame_focus(ctl,cam,focus2)
    laplac2 = laplacian2(frame)

    print(f"Min: {minfocus:.3f}, max: {maxfocus:.3f}, F1: {focus1:.3f}, F2: {focus2:.3f}, lap1: {laplac1}, lap2: {laplac2}")

    if laplac1 < laplac2:
        fine_focus_recursive(ctl,cam,focus1,maxfocus,mindiff)
    else:
        fine_focus_recursive(ctl,cam,minfocus,focus2,mindiff)



def fine_focus(ctl, cam, bestcroase,width,steps=10):
    minfocus = max(bestcroase-width/2,0)

    bestfocus = None
    bestlaplac = 0

    laplacs = []
    for i in range(steps+1):
        focus = minfocus + width*i/steps
        focus = min(focus,1)
        
        ret,frame = get_frame_focus(ctl,cam,focus)
        laplac = laplacian2(frame)
        laplacs.append(laplac)
        print(f"Focus: {focus}, laplac2: {laplac}")

        if laplac > bestlaplac:
            bestlaplac = laplac
            bestfocus = focus
        elif bestlaplac*0.75 > laplac:
            break


    laplacs.sort()
    threshold = laplacs[-2]*1.5

    focus = max(bestfocus-0.05,0)
    ret,frame = get_frame_focus(ctl,cam,focus)
    memlaplac = laplacian2(frame)
    while focus < bestfocus+0.05:
        
        ret,frame = get_frame_focus(ctl,cam,focus)
        laplac = laplacian2(frame)

        print(f"Focus: {focus}, laplac2: {laplac}")
        print(f"memlaplac: {memlaplac}, threshold: {threshold}")

        if memlaplac > laplac and memlaplac > threshold:
            ret,frame = get_frame_focus(ctl,cam,focus-0.025)
            laplac = laplacian2(frame)

            print(f"Final Focus: {focus-0.025}, laplac2: {laplac}")
            return

        focus +=0.005
        print(memlaplac,laplac)
        memlaplac = laplac
        
        if focus > 1:
            return



def get_frame_focus(ctl,cam,focus):
        ctl.set_focus(focus)
        ctl.waiting_for_free()
        for _ in range(12):
            ret,frame = cam.read()
        
        return cam.read()


        

def main():
    ctl = Controller(1)
    ctl.print_status()

    cam = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)


    for z in range(30,100):
        ctl.set_zoom(z/100)
        print(f"Zoom: {z/100}")
        
        croase = []
        for f in range(10):
            ret,frame = get_frame_focus(ctl,cam,f/10) 
            croase.append(laplacian2(frame))

            #print(f"Z: {z}, F: {f}, sobel: {sobel(frame)}, laplacian: {laplacian(frame)}, laplacian2: {laplacian2(frame)}")

        print(croase)
        bestfocus = find_peak(croase,10)
        print(f"Best croase: {bestfocus}")
        fine_focus(ctl,cam,bestfocus,0.2)

        fine_focus_recursive(ctl,cam,bestfocus-0.1, bestfocus+0.1)



if __name__ == '__main__':
    main()
