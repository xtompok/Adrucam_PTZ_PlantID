import cv2
import numpy as np

def sobel(img):
    img_gray = cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    img_sobel = cv2.Sobel(img_gray,cv2.CV_16U,1,1)
    return cv2.mean(img_sobel)[0]

def laplacian(img):
    img_gray = cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    img_sobel = cv2.Laplacian(img_gray,cv2.CV_16U)
    return cv2.mean(img_sobel)[0]
    
def laplacian2(img):
    img_gray = cv2.cvtColor(img,cv2.COLOR_RGB2GRAY) 
    img_sobel = cv2.Laplacian(img_gray,cv2.CV_64F).var()
    return img_sobel
