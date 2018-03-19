import logging
import time

import pygame
import cv2
import numpy as np

from dronecontrol import DroneControl
from dronevideo import DroneVideo


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    logging.info("Starting keyboard control app")
    pygame.init()
    screen = pygame.display.set_mode((576, 720))

    drone = DroneControl()
    drone.connect()

    video = DroneVideo()

    time.sleep(1.0)

    r = 127
    p = 127
    t = 127
    y = 127

    def clamp(n, minn, maxn): return max(min(maxn, n), minn)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                key = event.key

                if event.type == pygame.KEYDOWN:
                    direction = 1
                else:
                    direction = -1

                if key == 27:  # ESC
                    logging.info("[PC]: ESC exiting")
                    drone.stop()
                    drone.disconnect()
                    pygame.quit()
                elif key == 13:  # Enter
                    logging.info("[PC]: Enter")
                elif key == 119:  # w
                    p += direction*30
                elif key == 97:  # a
                    r -= direction*30
                elif key == 115:  # s
                    p -= direction*30
                elif key == 100:  # d
                    r += direction*30
                elif key == 274 and pygame.KEYDOWN:  # Down arrow
                    t -= 10
                elif key == 273 and pygame.KEYDOWN:  # Up arrow
                    t += 10
                elif key == 275:  # right arroww
                    y += direction*30
                elif key == 276:  # left arrow
                    y -= direction*30

                logging.debug("roll: {}, pitch: {}, throttle: {}, yaw: {}".format(r, p, t, y))
                r = clamp(r, 0, 255)
                p = clamp(p, 0, 255)
                t = clamp(t, 0, 255)
                y = clamp(y, 0, 255)

        drone.cmd(r, p, t, y)

        frame = video.get_last_image()
        if frame is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = np.flipud(np.rot90(frame))
            frame = pygame.surfarray.make_surface(frame)
            screen.blit(frame, (0,0))
            pygame.display.update()
