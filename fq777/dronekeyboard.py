import pygame
from dronecontrol import DroneControl

pygame.init()
pygame.display.set_mode((100, 100))


drone = DroneControl()
drone.connect()
drone.takeOff()

r = 127
p = 127
t = 127
y = 127

clamp = lambda n, minn, maxn: max(min(maxn, n), minn)

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

        if key == 27: #ESC
            print "[PC]: ESC exiting"
            drone.stop()
            drone.disconnect()
            pygame.quit()
        elif key == 13: #Enter
            print "[PC]: Enter"
        elif key == 119: #w
            p += direction*30
        elif key == 97: #a
            r -= direction*30
        elif key == 115: #s
            p -= direction*30
        elif key == 100: #d
            r += direction*30
        elif key == 274 and pygame.KEYDOWN: #Down arrow
            t -= 10
        elif key == 273 and pygame.KEYDOWN: #Up arrow
            t += 10
        elif key == 275: #right arroww
            y += direction*30
        elif key == 276: #left arrow
            y -= direction*30

        print r,p,t,y
        r = clamp(r, 0, 255)
        p = clamp(p, 0, 255)
        t = clamp(t, 0, 255)
        y = clamp(y, 0, 255)


  drone.cmd(r, p, t, y)