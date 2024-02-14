import cv2
import numpy as np
import time
import logging
from threading import Thread
from collections import deque
from platform import system
from time import sleep
from datetime import datetime
from tensorflow.keras.models import load_model
import tensorflow as tf
import requests
import json
from types import SimpleNamespace

class Camera:
    """
    Class responsible for handling input from the video source, detecting motion, saving videos.
    """

    def __init__(self, emergency_buff_size, detection_sensitivity, max_detection_sensitivity,
                 min_motion_contour_area, fps, camera_number, recording_mode):
        # logging
        self.__logger = logging.getLogger("security_camera_logger")

        # user's config
        self.min_motion_contour_area = min_motion_contour_area
        self.emergency_buff_size = emergency_buff_size
        self.detection_sensitivity = detection_sensitivity
        self.max_detection_sensitivity = max_detection_sensitivity
        self.camera_number = camera_number
        self.recording_mode = recording_mode

        # standard recording vars
        self.standard_recording_started = False
        self.__standard_recording_output = None
        self.standard_recording_fps = fps

        # emergency recording vars
        self.emergency_recording_started = False
        self.__emergency_recording_output = None
        self.__emergency_recording_buffered_frames = deque()
        self.emergency_recording_fps = fps
        self.emergency_file_path = None

        # capture config
        # todo: test h264 lib for linux
        if system() == "Windows":
            self.__fourcc_codec = cv2.VideoWriter_fourcc(*"h264")
            self.__capture = cv2.VideoCapture(self.camera_number, cv2.CAP_DSHOW)
            self.__logger.info("using h264 video codec on Windows")
        else:
            self.__fourcc_codec = cv2.VideoWriter_fourcc(*"mp4v")
            self.__capture = cv2.VideoCapture(self.camera_number)
            self.__logger.info("using mp4v video codec on Linux")
            
        HIGH_RES = 10000
        self.__capture.set(cv2.CAP_PROP_FRAME_WIDTH, HIGH_RES)
        self.__capture.set(cv2.CAP_PROP_FRAME_HEIGHT, HIGH_RES)
        
        self.frame_dimensions = (int(self.__capture.get(cv2.CAP_PROP_FRAME_WIDTH)), 
                                 int(self.__capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))

        self.__capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_dimensions[0])
        self.__capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_dimensions[1])

        # frames
        self.__frame_old = None
        self.__frame_new = None
        # self.model = load_model('inception_resnet_model.h5')
        self.class_label = ['non-violence' , 'violence']
        # modes
        self.frame_modes = {
                            "Standard": self.get_standard_frame,
                            }
        self.url ="http://127.0.0.1:5000/upload"
    def validate_capture(self):
        return self.__capture.isOpened()

    def destroy(self):
        """
        Stops emergency and standard recording, releases the capture, destroys the windows of OpenCV.
        :return: None
        """

        self.stop_emergency_recording()
        self.stop_standard_recording()
        self.__capture.release()
        cv2.destroyAllWindows()

        self.__logger.info("recordings stopped, camera destroyed")

    def refresh_frame(self):
        """
        Grabs new frame from the capture, updates emergency buffer.
        :return: True on success, False on fail
        """

        self.__frame_old = self.__frame_new
        try:
            success, self.__frame_new = self.__capture.read()
            cv2.putText(self.__frame_new, str(datetime.now())[:-7], (15, 35),
                        cv2.FONT_HERSHEY_PLAIN, 2.2, (255, 255, 255), 2, cv2.LINE_AA)
        except cv2.error:
            self.__logger.exception("failed to refresh frame")
            return False

        if success:
            if not self.emergency_recording_started:
                self.update_emergency_buffer()
        else:
            self.__logger.warning("failed to refresh frame")

        return success

    def update_emergency_buffer(self):
        frame_to_save = np.copy(self.get_frame_with_mode(self.recording_mode))

        if self.validate_frame(frame_to_save):
            self.__emergency_recording_buffered_frames.append(frame_to_save)

            if len(self.__emergency_recording_buffered_frames) > self.emergency_buff_size:
                self.__emergency_recording_buffered_frames.popleft()

    def show_window(self):
        """
        Shows standard OpenCV window with the captured frame.
        :return: None
        """
        if self.validate_frame(self.__frame_new):
            cv2.imshow("Capture", self.__frame_new)

    def preprocess_frame(self):
        frame = cv2.resize(self.__frame_new,(224,224))
        frame = np.array(frame) /255.0
        return frame
    def detect_violence(self):
        try:
            if not self.validate_frame(self.__frame_new) or not self.validate_frame(self.__frame_old):
                # self.__logger.warning("get_motion_contours() - failed to validate frames")
                return None
            _, img_encoded = cv2.imencode('.jpg', self.__frame_new)
            frame_bytes = img_encoded.tobytes()

            # Send the frame to Flask backend
            files = {'file': ('frame.jpg', frame_bytes, 'image/jpeg')}
            response = requests.post(self.url , files=files)
            if response.status_code == 200:
                print("Image sent successfully.")
                x = json.loads(response.content, object_hook=lambda d: SimpleNamespace(**d))
                print(x.result)
                if x.result == 'non-violence':
                    return False
                else:
                    return True
            else:
                print('Failed to send image to Flask server') 
        except Exception:
            print("Failed to send image to Flask server")    
    def get_motion_contours(self):
        """
        Looks for contours around places in the new frame that are different from the old frame.
        :return: list with contours on success, None if frames are corrupted / doesn't exist
        """

        if not self.validate_frame(self.__frame_new) or not self.validate_frame(self.__frame_old):
            # self.__logger.warning("get_motion_contours() - failed to validate frames")
            return None

        kernel = (3, 3)

        # hide timestamps
        frame_old = self.__frame_old.copy()
        cv2.rectangle(frame_old, (0, 0), (420, 50), (0, 0, 0), -1)
        frame_new = self.__frame_new.copy()
        cv2.rectangle(frame_new, (0, 0), (420, 50), (0, 0, 0), -1)

        # get difference between frames

        gray_diff = cv2.absdiff(self.convert_frame_to_gray_gb(frame_new, kernel),
                                self.convert_frame_to_gray_gb(frame_old, kernel))

        binary_diff = (
            cv2.threshold(gray_diff,
                          thresh=(self.max_detection_sensitivity + 1 - self.detection_sensitivity) *
                          self.max_detection_sensitivity,
                          maxval=255,
                          type=cv2.THRESH_BINARY))[1]

        binary_diff = cv2.dilate(binary_diff, np.ones(kernel), 1)

        return cv2.findContours(binary_diff, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE)[0]

    def get_motion_contours_with_min_area(self):
        """
        Looks for contours with minimum area around places in the new frame that are different from the old frame.
        :return: list with contours on success, None if frames are corrupted / doesn't exist
        """
        contours = self.get_motion_contours()

        if contours is not None:
            return tuple(filter(lambda c: cv2.contourArea(c) >= self.min_motion_contour_area, [c for c in contours]))

    def search_for_motion(self):
        """
        Checks if list of contours contains contour with min specified area.
        :return: True if contour with min specified area exists, False otherwise
        """

        contours = self.get_motion_contours_with_min_area()

        if contours is not None:
            return len(contours) > 0

        return False

    def write_standard_recording_frame(self):
        """
        Writes frame into the standard output video file. If output doesn't exist, creates a new one.
        :return: None
        """

        if not self.standard_recording_started:
            '''create new standard output'''

            self.standard_recording_started = True
            current_recording_time = time.strftime("%d-%m-%Y_%H-%M-%S", time.localtime(time.time()))
            recording_file_path = f"../recordings/standard/{current_recording_time}.mkv"
            self.__standard_recording_output = cv2.VideoWriter(recording_file_path, self.__fourcc_codec,
                                                               self.standard_recording_fps, self.frame_dimensions)

            self.__logger.info("standard recording started")

        frame_to_save = np.copy(self.get_frame_with_mode(self.recording_mode))

        if self.validate_frame(frame_to_save) and self.__standard_recording_output is not None:
            try:
                self.__standard_recording_output.write(frame_to_save)
            except cv2.error:
                self.__logger.exception("failed to write frame to standard recording")

    def save_emergency_recording_frame(self, controller):
        """
        Appends frame into emergency buffer and runs thread that writes buffered frames into emergency output video
        file. If output doesn't exist, creates a new one.
        :return: None
        """

        if not self.emergency_recording_started:
            '''create new emergency output'''

            self.emergency_recording_started = True
            current_recording_time = time.strftime("%d-%m-%Y_%H-%M-%S", time.localtime(time.time()))
            self.emergency_file_path = f"../recordings/emergency/{current_recording_time}.mkv"
            self.__emergency_recording_output = cv2.VideoWriter(self.emergency_file_path, self.__fourcc_codec,
                                                                self.emergency_recording_fps, self.frame_dimensions)

            emergency_buff_write_thread = Thread(target=self.write_emergency_buffer, args=(controller,))
            emergency_buff_write_thread.start()

            self.__logger.info("emergency recording started")

        frame_to_save = np.copy(self.get_frame_with_mode(self.recording_mode))
        self.__emergency_recording_buffered_frames.append(frame_to_save)

    def write_emergency_buffer(self, controller):
        """
        Writes buffered frames into emergency output file.
        :return: None
        """

        if self.__emergency_recording_output is not None:
            while (self.emergency_recording_started or len(self.__emergency_recording_buffered_frames) > 0) and \
                    controller.surveillance_running:
                if len(self.__emergency_recording_buffered_frames) > 0:
                    frame_to_save = self.__emergency_recording_buffered_frames.popleft()
                    if self.validate_frame(frame_to_save):
                        try:
                            self.__emergency_recording_output.write(frame_to_save)
                        except cv2.error:
                            self.__logger.exception("failed to write frame to emergency recording")
                    else:
                        self.__logger.warning("write_emergency_buffer() - failed to validate frames")

                sleep(0.0001)

    def stop_standard_recording(self):
        """
        Stops standard recording and releases standard recording output.
        :return: None
        """

        self.standard_recording_started = False
        if self.__standard_recording_output is not None:
            try:
                self.__standard_recording_output.release()
                self.__logger.info("standard recording stopped")
            except cv2.error:
                self.__logger.exception("failed to release standard recording output")

    def stop_emergency_recording(self):
        """
        Stops emergency recording and releases emergency recording output.
        :return: file path of emergency recording that just finished on success, None on fail
        """

        self.emergency_recording_started = False
        if self.__emergency_recording_output is not None:
            try:
                self.__emergency_recording_output.release()
                self.__logger.info("emergency recording stopped")
            except cv2.error:
                self.__logger.exception("failed to release emergency recording output")
                return None

        return self.emergency_file_path

    def save_frame_to_img(self, path):
        """
        Saves frame to specified location.
        :return: None
        """

        frame_to_save = np.copy(self.__frame_new)
        if self.validate_frame(frame_to_save):
            cv2.imwrite(path, frame_to_save)
        else:
            self.__logger.warning("save_frame_to_img() - failed to validate frame")

    @staticmethod
    def validate_frame(frame):
        return frame is not None and str(frame) != "None"

    @classmethod
    def get_number_of_camera_devices(cls):
        no_cameras = 0
        index = -1

        while True:
            cap = cv2.VideoCapture(index)

            if not cap.isOpened():
                break

            cap.release()

            no_cameras += 1
            index += 1

        return no_cameras

    '''Methods below are used to get and convert frames'''

    def get_standard_frame(self):
        frame = np.copy(self.__frame_new)
        if self.validate_frame(frame):
            return frame
        else:
            self.__logger.warning("get_standard_frame() - failed to validate frame")


    def get_frame_with_mode(self, mode):
        try:
            frame = self.frame_modes['Standard']()
        except KeyError:
            frame = self.get_standard_frame()

        return frame

    @staticmethod
    def convert_frame_to_gray_gb(frame, kernel):
        frame = np.copy(frame)
        if Camera.validate_frame(frame):
            return cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), kernel, sigmaX=0)
        else:
            logging.warning("convert_frame_to_gray_gb() - failed to validate frame")

    @staticmethod
    def convert_frame_to_rgb(frame):
        frame = np.copy(frame)
        if Camera.validate_frame(frame):
            return cv2.cvtColor(src=frame, code=cv2.COLOR_BGR2RGB)
        # else:
        #     logging.warning("convert_frame_to_rgb() - failed to validate frame")
