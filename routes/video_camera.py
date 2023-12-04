import cv2
import io
import os
import sys
import numpy as np
from threading import Condition
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
from libcamera import controls
from flask import current_app, render_template, Response, request
import json

print("Video mode: Camera")

def sortPoints(points):
    # We need to determine correct order of points
    # (top-left, top-right, bottom-right, and bottom-left)
    pts = points.reshape(4, 2)
    rect = np.zeros((4, 2), dtype = "float32")

    # The top-left point has the smallest sum whereas the
    # bottom-right has the largest sum
    s = pts.sum(axis = 1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # Compute the difference between the points -- the top-right
    # will have the minumum difference and the bottom-left will
    # have the maximum difference
    diff = np.diff(pts, axis = 1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect

def drawCorners(img, points):
    p1, p2, p3, p4 = map(tuple, points)

    # Draw outline
    pts = np.array([p1, p2, p3, p4], np.int32)
    pts = pts.reshape((-1,1,2))
    cv2.polylines(img, [pts], True, (0,255,0), 5)

    # Draw corners
    cv2.circle(img, p1, 7, (255, 0, 0), -1)
    cv2.circle(img, p2, 7, (255, 255, 255), -1)
    cv2.circle(img, p3, 7, (255, 255, 255), -1)
    cv2.circle(img, p4, 7, (255, 255, 255), -1)

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

# Video config helper functions
def app_file_path():
    # Get the app filepath
    fn = getattr(sys.modules['__main__'], '__file__')
    root_path = os.path.abspath(os.path.dirname(fn))
    return root_path

def get_video_config_filepath():
    video_filepath = os.path.join(app_file_path(), current_app.video_config_filepath)
    return video_filepath

def get_mouse_config_filepath():
    mouse_filepath = os.path.join(app_file_path(), current_app.mouse_config_filepath)
    return mouse_filepath

# Set up temp config data
last_video_size = {"o": "", "x":0, "y":0, "w": 0, "h":0}

saved_box_points = []

picam2 = Picamera2()
config = picam2.create_video_configuration(main={
    "size": (1920, 1080),
    "format": "XRGB8888"
    })
print(config)
picam2.configure(config)
picam2.set_controls({"AfMode": controls.AfModeEnum.Manual,
                     "LensPosition": 3.5,
                     #"ExposureTime": 80000,
                     #"Brightness": -.5
                     })
output = StreamingOutput()
picam2.start_recording(MJPEGEncoder(), FileOutput(output))

def api_config_video():
    global saved_box_points

    for i in range(5):
        im = picam2.capture_array()

    # Make it easier to process
    rotated = cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)
    gray = cv2.cvtColor(rotated, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    thresh = cv2.adaptiveThreshold(blur, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    thresh = cv2.bitwise_not(thresh)
    edge = cv2.Canny(thresh, 1, 255)
    contours, hierarchy = cv2.findContours(edge.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rects = []
    rect_count = 0
    for i, contour in enumerate(contours):
        approx = cv2.approxPolyDP(contour, 0.1*cv2.arcLength(contour, True), True)
        if len(approx) == 4:
            area = cv2.contourArea(contour)
            if area > 4000:
                break

    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    box = sortPoints(box)
    saved_box_points = box

    return Response(mimetype="application/json")


def api_screenshot():
    global saved_box_points
    path = request.path

    for i in range(5):
        im = picam2.capture_array()

    # Make it easier to process
    rotated = cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)
    gray = cv2.cvtColor(rotated, cv2.COLOR_RGB2GRAY)

    if saved_box_points == []:
        print("No saved box points, yet")
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        thresh = cv2.adaptiveThreshold(blur, 255,
                                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        thresh = cv2.bitwise_not(thresh)
        edge = cv2.Canny(thresh, 1, 255)
        contours, hierarchy = cv2.findContours(edge.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rects = []
        rect_count = 0
        for i, contour in enumerate(contours):
            approx = cv2.approxPolyDP(contour, 0.1*cv2.arcLength(contour, True), True)
            if len(approx) == 4:
                area = cv2.contourArea(contour)
                if area > 4000:
                    break

        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        box = sortPoints(box)

        # Draw shape outline
        #cv2.drawContours(rotated,[contour],0,(0,255,255),5)
        # Draw rectangle
        #cv2.drawContours(rotated,[np.intp(box)],0,(0,255,255),5)
    else:
        print("Box points are saved!")
        box = saved_box_points

    refPoints = np.array([(0,0),(1080,0),(1080,2408),(0,2408)], dtype="float32")
    transform = cv2.getPerspectiveTransform(box, refPoints)
    warp = cv2.warpPerspective(rotated, transform, (1080, 2408))
    alpha = 1.3 # Contrast control (1.0-3.0)
    beta = 30 # Brightness control (0-100)
    adjusted = cv2.convertScaleAbs(warp, alpha=alpha, beta=beta)

    if "gray" in path:
        adjusted = cv2.cvtColor(adjusted, cv2.COLOR_RGB2GRAY)

    success, buffer = cv2.imencode('.png', adjusted)
    response = Response(buffer.tobytes(), mimetype='image/png')
    response.headers['Content-Length'] = len(buffer)
    return response

# Cropped video
def stream():
    return render_template('stream.html', style="crop")

def video_feed():
    video_config_filepath = get_video_config_filepath()
    return Response(gen_frames(style = "crop",
                               video_config = video_config_filepath),
                               mimetype='multipart/x-mixed-replace; boundary=frame')

# Raw video
def raw_stream():
    return render_template('stream.html', style="raw")

def raw_video_feed():
    video_config_filepath = get_video_config_filepath()
    return Response(gen_frames(style = "raw",
                               mouse_config = "",
                               video_config = video_config_filepath),
                               mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames(style = "crop", mouse_config="", video_config=""):
    while True:
        im = picam2.capture_array()

        if style == "raw":
            # Okay, fine, we'll rotate it, but that's it.
            rotated = cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)
            # Okay, make is smaller so it's easier to stream, but that's it.
            height, width, channels = rotated.shape
            smaller = cv2.resize(rotated, (int(width*.4), int(height*.4)))
            success, buffer = cv2.imencode('.jpg', smaller)
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        else:
            # Make it easier to process
            rotated = cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)
            gray = cv2.cvtColor(rotated, cv2.COLOR_RGB2GRAY)
            blur = cv2.GaussianBlur(gray, (5,5), 0)
            thresh = cv2.adaptiveThreshold(blur, 255,
                                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            thresh = cv2.bitwise_not(thresh)
            edge = cv2.Canny(thresh, 1, 255)
            contours, hierarchy = cv2.findContours(edge.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            rects = []
            rect_count = 0
            for i, contour in enumerate(contours):
                approx = cv2.approxPolyDP(contour, 0.1*cv2.arcLength(contour, True), True)
                if len(approx) == 4:
                    area = cv2.contourArea(contour)
                    if area > 4000:
                        break

            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = sortPoints(box)

            # Draw shape outline
            #cv2.drawContours(rotated,[contour],0,(0,255,255),5)
            # Draw rectangle
            #cv2.drawContours(rotated,[np.intp(box)],0,(0,255,255),5)

            #refPoints = np.array([(0,0),(1080,0),(1080,2408),(0,2408)], dtype="float32")
            refPoints = np.array([(0,0),(540,0),(540,1204),(0,1204)], dtype="float32")
            transform = cv2.getPerspectiveTransform(box, refPoints)
            #warp = cv2.warpPerspective(rotated, transform, (1080, 2408))
            warp = cv2.warpPerspective(rotated, transform, (540, 1204))
            alpha = 1.3 # Contrast control (1.0-3.0)
            beta = 30 # Brightness control (0-100)
            adjusted = cv2.convertScaleAbs(warp, alpha=alpha, beta=beta)

            success, buffer = cv2.imencode('.jpg', adjusted)
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')