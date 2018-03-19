import socket
import time
import threading
import logging

import numpy as np
import cv2
try:
    import gi
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst
except ImportError:
    logging.error("Couldn't open gstreamer")

import droneconfig


class DroneVideo(threading.Thread):
    """This handles connecting to and parsing the video coming off of the drone.
    """
    def __init__(self):
        super(DroneVideo, self).__init__()
        logging.info("Starting drone video")
        self.ip = '172.16.10.1'
        self.port = 8888
        self.daemon = True

        # The video is in h264 format coming from the drone.
        # This gstreamer pipeline decodes the h264 frames and
        # converts them to BGR to be used with opencv
        Gst.init([])
        self.source = Gst.ElementFactory.make("appsrc", "vidsrc")
        parser = Gst.ElementFactory.make("h264parse", "h264parser")
        decoder = Gst.ElementFactory.make("avdec_h264", "h264decoder")
        convert = Gst.ElementFactory.make("videoconvert", "yuv_to_rgb")
        self.output = Gst.ElementFactory.make("appsink")
        caps = Gst.caps_from_string("video/x-raw, format=(string)BGR;")
        self.output.set_property("caps", caps)
        self.output.set_property("emit-signals", True)
        self.output.connect("new-sample", self.new_buffer, self.output)

        # Add elements to pipeline
        self.pipeline = Gst.Pipeline.new()
        self.pipeline.add(self.source)
        self.pipeline.add(parser)
        self.pipeline.add(decoder)
        self.pipeline.add(convert)
        self.pipeline.add(self.output)

        # Link the elements
        self.source.link(parser)
        parser.link(decoder)
        decoder.link(convert)
        convert.link(self.output)

        self.image_arr = None
        self.pipeline.set_state(Gst.State.PLAYING)
        self.last_image_ts = time.time()
        self.open_connections()
        self.start()

    def open_connections(self):
        # Like the drone control, this performs handshaking for the
        # video stream.
        self.video = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.video.connect((self.ip, self.port))
        self.video.send(droneconfig.VIDEO_INITIALIZE[0])
        logging.info("video link 1: {}".format(len(self.video.recv(8192))))
        self.video.send(droneconfig.VIDEO_INITIALIZE[1])
        logging.info("video link 2: {}".format(len(self.video.recv(8192))))

        # This is the actual stream for the video frames
        self.stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.stream.connect((self.ip, self.port))
        self.stream.send(droneconfig.STREAM_START)
        self.stream.settimeout(5)

        # Hearbeat must be started last, this keeps the video stream alive.
        self.heartbeat = DroneHeartbeat()

    def new_buffer(self, sink, data):
        """Callback for a new frame from the gstreamer
        pipeline.
        """
        sample = self.output.emit("pull-sample")
        arr = self.gst_to_opencv(sample)
        self.image_arr = arr
        self.last_image_ts = time.time()
        return Gst.FlowReturn.OK

    def gst_to_opencv(self, sample):
        """Convert the gstreamer frame to an opencv image (numpy array).
        """
        buf = sample.get_buffer()
        caps = sample.get_caps()

        arr = np.ndarray(
            (caps.get_structure(0).get_value('height'),
             caps.get_structure(0).get_value('width'),
             3),
            buffer=buf.extract_dup(0, buf.get_size()),
            dtype=np.uint8)
        return arr

    def run(self):
        """Video thread
        """
        while True:
            try:
                data = self.stream.recv(8192)
                logging.debug("New video data of length: {}".format(len(data)))
                buf = Gst.Buffer.new_allocate(None, len(data), None)
                assert buf is not None
                buf.fill(0, data)
                self.source.emit("push-buffer", buf)

            except socket.timeout:
                logging.error("timeout: {}".format(time.time() - self.start_time))
                self.stream.close()
                self.video.close()
                return

    def get_last_image(self):
        return self.image_arr

    def get_last_ts(self):
        return self.last_image_ts


class DroneHeartbeat(threading.Thread):
    """This keeps the video connection alive.  Without it, the video stream
    will stop after 30 seconds.
    """
    def __init__(self):
        super(DroneHeartbeat, self).__init__()
        self.ip = '172.16.10.1'
        self.port = 8888
        self.daemon = True
        self.last_beat = time.time()
        self.start()

    def run(self):
        """Send the heartbeat signal once every HEARBEAT_RATE seconds
        """
        heartbeat = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        heartbeat.connect((self.ip, self.port))
        heartbeat.send(droneconfig.HEARTBEAT)
        logging.info("Heartbeat: {}".format(len(heartbeat.recv(8192))))
        while True:
            try:
                if time.time() - self.last_beat > droneconfig.HEARTBEAT_RATE:
                    logging.debug("Heartbeat: {}".format(time.time()))
                    heartbeat.send(droneconfig.HEARTBEAT)
                    self.last_beat = time.time()
            except socket.timeout:
                heartbeat.close()
                return


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dv = DroneVideo()
    while True:
        im = dv.get_last_image()
        if im is not None:
            cv2.imshow('frame', im)
            cv2.waitKey(1)
