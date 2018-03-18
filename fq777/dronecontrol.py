import socket
import time
import logging

import droneconfig

class DroneControl(object):
    def __init__(self):
        self._ip = '172.16.10.1'
        self._tcp_port = 8888
        self._udp_port = 8895

    def connect(self):
        self.connect_tcp()
        self.connect_udp()
        self.droneCmd = droneconfig.FLY_DRONE_DATA[:]

    def connect_tcp(self): # handshake
        logging.info("Starting Handshake...")
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.connect((self._ip, self._tcp_port))
        self.tcp_socket.send(droneconfig.HANDSHAKE_DATA)
        logging.info("Handshake done!")

    def connect_udp(self):
        logging.info("Starting drone...")
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.connect((self._ip, self._udp_port))
        self.droneCmd = droneconfig.START_DRONE_DATA[:]
        self.udp_socket.send(self.droneCmd)
        logging.info("Drone started!")

    def checksum(self, data):
        return_data = (data[1] ^ data[2] ^ data[3] ^ data[4] ^ data[5]) & 0xFF;
        return return_data

    def disconnect(self):
        logging.info("Disconnecting...")
        self.udp_socket.close()
        self.tcp_socket.close()
        logging.info("Disconnected!")

    def cmd(self, r=127, p=127, t=15, y=127): # roll, pitch, throttle, yaw
        self.droneCmd[1] = r
        self.droneCmd[2] = p
        self.droneCmd[3] = t
        self.droneCmd[4] = y
        self.droneCmd[6] = self.checksum(self.droneCmd)
        self.udp_socket.send(self.droneCmd)

    def takeOff(self):
        logging.info("taking off")
        takeOffCmd = droneconfig.FLY_DRONE_DATA
        for i in xrange(16):
            self.udp_socket.send(takeOffCmd)
        logging.info("done taking off")

    def land(self):
        landCmd = droneconfig.LAND_DRONE_DATA
        for i in xrange(16):
            self.udp_socket.send(landCmd)

    def stop(self):
        self.udp_socket.send(droneconfig.START_DRONE_DATA)


if __name__ == "__main__":
    drone = DroneControl()
    drone.connect()

    for i in range(100):
        drone.cmd(t=100)

    drone.stop()
    drone.disconnect()
