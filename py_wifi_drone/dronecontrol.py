import socket
import logging

import droneconfig


class DroneControl(object):
    """This is the base drone control app, it handles connecting to the drone
    and sending necessary commands for controlling the drone
    """

    def __init__(self):
        self._ip = '172.16.10.1'
        self._tcp_port = 8888
        self._udp_port = 8895
        self.is_connected = False

    def connect(self):
        """Kicks off the connection on the tcp and udp ports.  This must be run
        before attempting to send control commands to the quadcopter.
        """
        self.connect_tcp()
        self.connect_udp()

    def connect_tcp(self):
        """This is just an initial handshake between the computer and the drone.the
        The actual flight data is send over the udp connection.
        """
        logging.info("Starting Handshake...")
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.connect((self._ip, self._tcp_port))
        self.tcp_socket.send(droneconfig.HANDSHAKE_DATA)
        logging.info("Handshake done!")

    def connect_udp(self):
        """Connects the udp port that the drone flight commands are sent over.
        """
        logging.info("Starting drone...")
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.connect((self._ip, self._udp_port))
        droneCmd = droneconfig.START_DRONE_DATA[:]
        self.udp_socket.send(droneCmd)
        logging.info("Drone started!")

    def checksum(self, data):
        """The flight data has to be passed through a checksum before it will run.
        Not sure why this is necessary as udp automatically ensures a checksum.

        Returns:
            the 8 bit xor checksum of the data
        """
        return_data = (data[1] ^ data[2] ^ data[3] ^ data[4] ^ data[5]) & 0xFF
        return return_data

    def disconnect(self):
        """This should be run if the user wishes to disconnect the drone from the program.
        If this program is killed, however, it should automatically disconnect.
        """
        logging.info("Disconnecting...")
        self.udp_socket.close()
        self.tcp_socket.close()
        logging.info("Disconnected!")

    def cmd(self, r=127, p=127, t=15, y=127):
        """This is the flight command controls.

        Args:
            r (int): 0-255 for the roll of the drone, 127 is the middle
            p (int): 0-255 for the pitch of the drone, 127 is the middle
            t (int): 0-255 for the throttle of the drone, 0 is no throttle
            y (int): 0-255 for the yaw of the drone, 127 is middle
        """
        droneCmd = droneconfig.FLY_DRONE_DATA[:]
        droneCmd[1] = r
        droneCmd[2] = p
        droneCmd[3] = t
        droneCmd[4] = y
        droneCmd[6] = self.checksum(droneCmd)
        self.udp_socket.send(droneCmd)

    def take_off(self):
        """Sends the takeoff command for the drone
        """
        logging.info("taking off")
        takeOffCmd = droneconfig.FLY_DRONE_DATA
        # We send 16 packets as this is udp and there is the possibility of
        # dropping them
        for i in xrange(16):
            self.udp_socket.send(takeOffCmd)
        logging.info("done taking off")

    def land(self):
        """Send the land command for the drone
        """
        landCmd = droneconfig.LAND_DRONE_DATA
        # We send 16 packets as this is udp and there is the possibility of
        # dropping them
        for i in xrange(16):
            self.udp_socket.send(landCmd)

    def stop(self):
        """This is a hard stop for the drone.  If it is flying and this is called,
        it will fall out of the air.
        """
        for i in xrange(16):
            self.udp_socket.send(droneconfig.START_DRONE_DATA)


if __name__ == "__main__":
    drone = DroneControl()
    drone.connect()

    for i in range(100):
        drone.cmd(t=100)

    drone.land()
    drone.stop()
    drone.disconnect()
