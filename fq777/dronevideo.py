import socket
import time
import threading
import logging

import numpy as np
import cv2
try:
    import gi
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst, GLib
except ImportError:
    logging.error("Couldn't open gstreamer")

import droneconfig


class DroneVideo(threading.Thread):
    def __init__(self):
        super(DroneVideo, self).__init__()
        self.ip = '172.16.10.1'
        self.port = 8888
        self.daemon = True

        Gst.init([])  # init gstreamer
        self.source = Gst.ElementFactory.make("appsrc", "vidsrc")
        parser = Gst.ElementFactory.make("h264parse", "h264parser")
        decoder = Gst.ElementFactory.make("avdec_h264", "h264decoder")
        convert = Gst.ElementFactory.make("videoconvert", "yuv_to_rgb")
        self.output = Gst.ElementFactory.make("appsink")
        caps = Gst.caps_from_string("video/x-raw, format=(string)BGR;")
        self.output.set_property("caps", caps)
        self.output.set_property("emit-signals", True)
        self.output.connect("new-sample", self.new_buffer, self.output)

        self.pipeline = Gst.Pipeline.new()
        self.pipeline.add(self.source)
        self.pipeline.add(parser)
        self.pipeline.add(decoder)
        self.pipeline.add(convert)
        self.pipeline.add(self.output)

        # # Link the elements
        self.source.link(parser)
        parser.link(decoder)
        decoder.link(convert)
        convert.link(self.output)

        self.image_arr = None
        self.last_send = time.time()

        self.pipeline.set_state(Gst.State.PLAYING)
        self.start_time = time.time()
        self.last_image_ts = time.time()
        self.start()

    def new_buffer(self, sink, data):
        sample = self.output.emit("pull-sample")
        arr = self.gst_to_opencv(sample)
        self.image_arr = arr
        self.last_image_ts = time.time()
        return Gst.FlowReturn.OK

    def gst_to_opencv(self, sample):
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
        count = 0
        video = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        video.connect((self.ip, self.port))

        video.send(droneconfig.VIDEO_INITIALIZE[0])
        logging.info("video link 1:", len(video.recv(8192)))
        video.send(droneconfig.VIDEO_INITIALIZE[1])
        logging.info("video link 2:", len(video.recv(8192)))

        stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stream.connect((self.ip, self.port))
        stream.send(droneconfig.STREAM_START)
        stream.settimeout(5)

        heartbeat = DroneHeartbeat()

        while True:
            try:
                data = stream.recv(8192)
                buf = Gst.Buffer.new_allocate(None, len(data), None)
                assert buf is not None
                buf.fill(0, data)
                self.source.emit("push-buffer", buf)

            except socket.timeout:
                logging.error("timeout: {}".format(time.time() - self.start_time))
                stream.close()
                video.close()
                return


class DroneHeartbeat(threading.Thread):
    def __init__(self):
        super(DroneHeartbeat, self).__init__()
        self.ip = '172.16.10.1'
        self.port = 8888
        self.daemon = True
        self.last_beat = time.time()
        self.start()

    def run(self):
        heartbeat = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        heartbeat.connect((self.ip, self.port))
        heartbeat.send(droneconfig.HEARTBEAT)
        logging.info("Heartbeat: {}".format(len(heartbeat.recv(8192))))
        while True:
            try:
                if time.time() - self.last_beat > droneconfig.HEARTBEAT_RATE:
                    heartbeat.send(droneconfig.HEARTBEAT)
                    self.last_beat = time.time()
            except socket.timeout:
                heartbeat.close()
                return


if __name__ == "__main__":
    dv = DroneVideo()
    while True:
        im = dv.image_arr
        if im is not None:
            cv2.imshow('frame', im)
            cv2.waitKey(1)
