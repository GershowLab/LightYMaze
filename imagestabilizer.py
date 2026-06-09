import cv2
import numpy as np
from PIL.ImageTransform import AffineTransform

from affinecalculator import AffineCalculator


class ImageStabilizer(object):
    def __init__(self, template_image):
        self.template = np.asarray(template_image.copy(), np.float32)
        self.roi = [] #x,y,w,h
        self.hw = []
        self.H = np.array(((1,0,0),(0,1,0))) #transformation to apply to image to align it to template
        self.HINV = self.H.copy() #transformation to apply to template points to produce image points

    def add_roi(self, roi): #x,y,w,h
        roi = np.asarray(roi, np.uint32)
        if np.any(roi[2:] <= 0):
            print ("zero passed for roi dimension")
            return
        self.roi.append(roi)
#        w,h = roi[2],roi[3]
        self.hw.append(cv2.createHanningWindow(roi[2:], cv2.CV_32F))

    def register_roi(self, im, roi, hw):
        delta = np.round(self.HINV@np.array((roi[0],roi[1],1)) - roi[:2]).astype(np.int32)
        x,y,w,h = roi.astype(int)
        delta[0] = np.minimum(np.maximum(delta[0], -x), im.shape[1]-x-w)
        delta[1] = np.minimum(np.maximum(delta[1], -y), im.shape[0] - y - h)

        # delta[0] = np.clip(delta[0], -x, im.shape[1]-x-w)
        #delta[1] = np.clip(delta[1], -y, im.shape[0]-y-h)

        imsub = np.asarray(im[(delta[1]+y):(delta[1] + y+h), (delta[0]+x):(delta[0]+x + w)], np.float32) #image location
        tempsub = np.asarray(self.template[y:(y+h), x:(x+w)], np.float32)
        return cv2.phaseCorrelate(tempsub, imsub,hw)[0]+ delta #displacement from template to image

    def find_transform(self, im):
        srcpts = []
        dstpts = []
        for j in range(len(self.roi)):
            r = self.roi[j]
            ctr = np.array((r[0]+r[2]/2, r[1]+r[3]/2))
            delta = self.register_roi(im, r, self.hw[j])
            srcpts.append(ctr) #location in template
            dstpts.append(ctr + np.asarray(delta)) #location in image
        self.H = cv2.estimateAffine2D(np.asarray(dstpts),np.asarray(srcpts), method=cv2.RANSAC)[0]
        h = np.eye(3)
        h[:2,:] = self.H
        self.HINV = np.linalg.inv(h)[:2,:]
        return self.H

    def apply_transform(self, im, alpha_update = 0):
        newim = cv2.warpAffine(im, self.H, (self.template.shape[1],self.template.shape[0]), flags=cv2.INTER_LINEAR)
        if alpha_update > 0:
            self.template = self.template*(1-alpha_update) + alpha_update*np.asarray(newim, np.float32)
        return newim

    def register(self,im, alpha_update = 0):
        self.find_transform(im)
        return self.apply_transform(im, alpha_update)
