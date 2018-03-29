import sys

import cv2
import numpy as np
from mpl_toolkits.mplot3d import axes3d
import matplotlib.pyplot as plt

from py_wifi_drone import dronevideo

class EgoMotion:
    def __init__(self, camera_mat):
        self.scale = 1.0
        self.last_image = None
        self.prev_points = []
        self.current_position = np.array([0.0, 0.0, 0.0])
        self.current_rotation = np.eye(3)
        self.camera_mat = camera_mat

    def detect_features(self, image):
        kpts = cv2.goodFeaturesToTrack(image,
                                       maxCorners = 100,
                                       qualityLevel = 0.1,
                                       minDistance = 4,
                                       blockSize = 7)
        return kpts

    def track_features(self, image):
        newPts, status, err = cv2.calcOpticalFlowPyrLK(self.last_image,
                                                       image,
                                                       self.prev_points,
                                                       None,
                                                       winSize=(21, 21),
                                                       maxLevel=3,
                                                       minEigThreshold=0.001)
        return newPts

    def update_image(self, new_image):
        if self.last_image is None or len(self.prev_points) < 10:
            self.last_image = new_image
            self.prev_points = self.track_features(new_image)
            return self.current_position

        new_points = self.track_features(new_image)
        E, mask = cv2.findEssentialMat(self.prev_points,
                                       new_points,
                                       self.camera_mat)

        self.prev_points = new_points
        pose, R, t, mask = cv2.recoverPose(E, prevPts, newPts, focal=657.30254, pp=(360, 240))

        self.current_rotation = np.dot(R, self.current_rotation)
        self.current_position += np.dot(self.current_rotation, t)

        return self.current_position


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "format is python egomotion.py calib.yaml"
    fs = cv2.FileStorage(sys.argv[1], cv2.FILE_STORAGE_READ)
    camera_mat = fs.getNode("K").mat()
    fs.release()

    dv = dronevideo.DroneVideo()
    em = EgoMotion(camera_mat)
    last_ts = None
    idx = 0

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    pts = []

    while True:
        im = dv.get_last_image()
        if im is not None:
            if last_ts != dv.last_image_ts:
                last_ts = dv.last_image_ts
                position = em.update_image(im)
                pts.append(position)



