#!/usr/bin/env python

from autofocus_math import sobel, laplacian, laplacian2
from control import Controller
from capture import gstreamer_pipeline
import time
import cv2

SUFFICIENT_FOCUS = 80
CROASE_STEPS = 10


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
    if bestidx is None:
        return None,None
    return (bestidx)/nsteps,vals[bestidx]

def fine_focus_recursive(ctl,cam,minfocus,maxfocus,mindiff=0.01):
    if (maxfocus-minfocus < mindiff):
        return

    step = max((maxfocus-minfocus)/10,0.005)

    focus1 = max((minfocus+maxfocus)/2-step/2,0)
    focus2 = min((minfocus+maxfocus)/2+step/2,1)
    
    ret,frame = get_frame_at_focus(ctl,cam,focus1)
    laplac1 = laplacian2(frame)
    ret,frame = get_frame_at_focus(ctl,cam,focus2)
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
        
        ret,frame = get_frame_at_focus(ctl,cam,focus)
        laplac = laplacian2(frame)
        laplacs.append(laplac)
#        print(f"Focus: {focus}, laplac2: {laplac}")
        
        if laplac > SUFFICIENT_FOCUS:
            return focus,laplac

        if laplac > bestlaplac:
            bestlaplac = laplac
            bestfocus = focus
        elif bestlaplac*0.75 > laplac:
            break


    laplacs.sort()
    threshold = laplacs[-2]*1.5

    focus = max(bestfocus-0.02,0)
    ret,frame = get_frame_at_focus(ctl,cam,focus)
    memlaplac = laplacian2(frame)
#    print(f"Focus: {focus}, Memlaplac: {memlaplac}")
    while focus < bestfocus+0.02:
        
        ret,frame = get_frame_at_focus(ctl,cam,focus)
        laplac = laplacian2(frame)

#        print(f"Focus: {focus}, laplac2: {laplac}")

        if laplac > SUFFICIENT_FOCUS:
            return focus,laplac

        if memlaplac-5 > laplac and memlaplac > threshold:
            ctl.set_focus(focus-0.05)
            final = focus-0.005
            ret,frame = get_frame_at_focus(ctl,cam,final)
            laplac = laplacian2(frame)

            print(f"Final Focus: {final}, laplac2: {laplac}")
            return final,laplac

        focus +=0.005
        memlaplac = laplac
        
        if focus > 1:
            return focus,laplac
    return None, None



def get_frame_at_focus(ctl,cam,focus):
        ctl.set_focus(focus)
        ctl.waiting_for_free()
        time.sleep(0.1)
        for _ in range(2):
            ret,frame = cam.read()
        
        return cam.read()

def croase_focus(ctl,cam,steps):
        croase = []
        for f in range(steps):
            ret,frame = get_frame_at_focus(ctl,cam,f/steps) 
            croase.append(laplacian2(frame))
        
        print(croase)
        return find_peak(croase,steps)


def autofocus(ctl,cam):
    croase,val = croase_focus(ctl,cam,CROASE_STEPS)
    if croase is None:
        return None,None
    fine,val = fine_focus(ctl,cam,croase,2/CROASE_STEPS)
    return fine,val

def detailed_autofocus(ctl,cam):
    croase,val = croase_focus(ctl,cam,CROASE_STEPS*3)
    if croase is None:
        return None,None
    fine,val = fine_focus(ctl,cam,croase,2/(CROASE_STEPS*3))
    return fine,val
        

def main():
    ctl = Controller(1)
    ctl.print_status()

    cam = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)


    for z in range(0,100):
        ctl.set_zoom(z/100)
        print(f"Zoom: {z/100}")
        

            #print(f"Z: {z}, F: {f}, sobel: {sobel(frame)}, laplacian: {laplacian(frame)}, laplacian2: {laplacian2(frame)}")

        focus,val = autofocus(ctl,cam)
        print(f"Focus: {focus}, laplac: {val}")
        ret,frame = cam.read()
        print(ret,int(time.time()))
        cv2.imwrite(f'/tmp/ram/{int(time.time())}.jpg',frame)
        #fine_focus_recursive(ctl,cam,bestfocus-0.1, bestfocus+0.1)



if __name__ == '__main__':
    main()
