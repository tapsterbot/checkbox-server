import cv2
import io
import os
import sys
import time
import numpy as np
from threading import Condition, Lock, Thread
from picamera2 import Picamera2, MappedArray
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
from libcamera import controls
from flask import current_app, render_template, Response, request
import json

print("Video mode: Camera")

# Keep OpenCV on one thread, spreading each small frame over every core
# costs more CPU overall and leaves less room for other processes
cv2.setNumThreads(1)

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

def unrotatePoints(points, width):
    # Map points in the 90° counterclockwise rotated frame back to the
    # unrotated camera frame, so the rotation can be folded into the warp
    return np.array([(width - 1 - y, x) for x, y in points], dtype = "float32")

def findScreenBox(gray):
    # Find the phone screen in a gray, 90° counterclockwise rotated frame
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    thresh = cv2.adaptiveThreshold(blur, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    thresh = cv2.bitwise_not(thresh)
    edge = cv2.Canny(thresh, 1, 255)
    contours, hierarchy = cv2.findContours(edge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 0:
        return None

    # Check the area first, it's much cheaper than approxPolyDP
    # and there can be tens of thousands of contours
    for i, contour in enumerate(contours):
        if cv2.contourArea(contour) > 4000:
            approx = cv2.approxPolyDP(contour, 0.1*cv2.arcLength(contour, True), True)
            if len(approx) == 4:
                break

    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    return sortPoints(box)

def findScreen(gray, found_box):
    box = findScreenBox(cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE))
    if box is not None:
        found_box[0] = box

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

# How often to look for the phone screen again, in seconds
screen_check_interval = 1.0

# Stream settings, changed from the HUD and saved in the video config file
raw_sizes = {"small": (384, 216), "medium": (768, 432), "large": (1280, 720)}
crop_sizes = {"small": (270, 602), "medium": (540, 1204), "large": (1080, 2408)}
max_fps = 30
stream_settings = {
    # The raw fps is the camera frame rate, so it also caps the cropped stream
    "raw": {"fps": 15, "size": "medium", "gray": False},
    "crop": {"fps": 10, "size": "medium", "gray": False},
}
settings_lock = Lock()

picam2 = Picamera2()
output = StreamingOutput()
# Held while capturing, so the camera can be restarted safely
camera_lock = Lock()

def frameDuration(fps):
    us = int(1000000 / fps)
    return (us, us)

def start_camera():
    # main: full quality frames for screenshots and the cropped stream
    # lores: small frames, hardware encoded to MJPEG for the raw stream
    config = picam2.create_video_configuration(main={
        "size": (1920, 1080),
        "format": "XRGB8888"
        },
        lores={"size": raw_sizes[stream_settings["raw"]["size"]]})
    print(config)
    picam2.configure(config)
    picam2.set_controls({"AfMode": controls.AfModeEnum.Manual,
                         "LensPosition": 3.5,
                         "FrameDurationLimits": frameDuration(stream_settings["raw"]["fps"]),
                         #"ExposureTime": 80000,
                         #"Brightness": -.5
                         })
    picam2.start_encoder(MJPEGEncoder(), FileOutput(output), name="lores")
    picam2.start()

def restart_camera():
    with camera_lock:
        picam2.stop_encoder()
        picam2.stop()
        start_camera()

def checkStreamSettings(new):
    # Returns the merged settings, or raises ValueError without changing anything
    if not isinstance(new, dict):
        raise ValueError("settings must be a JSON object")
    updated = {name: dict(values) for name, values in stream_settings.items()}
    for name, sizes in (("raw", raw_sizes), ("crop", crop_sizes)):
        values = new.get(name, {})
        if not isinstance(values, dict):
            raise ValueError("%s must be a JSON object" % name)
        for key, value in values.items():
            if key == "fps":
                if isinstance(value, bool) or not isinstance(value, (int, float)) or \
                   not 1 <= value <= max_fps:
                    raise ValueError("%s.fps must be a number from 1 to %d" % (name, max_fps))
            elif key == "size":
                if value not in sizes:
                    raise ValueError("%s.size must be one of: %s" % (name, ", ".join(sizes)))
            elif key == "gray":
                if not isinstance(value, bool):
                    raise ValueError("%s.gray must be true or false" % name)
            else:
                raise ValueError("unknown setting: %s.%s" % (name, key))
            updated[name][key] = value
    return updated

def load_stream_settings(video_config_filepath, crop_fps=None):
    # Called by server.py before start_camera()
    try:
        with open(os.path.join(app_file_path(), video_config_filepath)) as f:
            saved = json.load(f).get("stream", {})
        stream_settings.update(checkStreamSettings(saved))
    except (OSError, ValueError) as e:
        print("Using default stream settings:", e)
    if crop_fps is not None:
        stream_settings["crop"]["fps"] = crop_fps
    print("Stream settings:", stream_settings)

def save_stream_settings():
    # Only replace our own section, the rest is the HDMI video config
    video_config_filepath = get_video_config_filepath()
    with open(video_config_filepath) as f:
        video_config_data = json.load(f)
    video_config_data["stream"] = stream_settings
    with open(video_config_filepath, "w") as f:
        f.write(json.dumps(video_config_data, indent=2))

def api_config_stream():
    if request.method == "POST":
        with settings_lock:
            try:
                updated = checkStreamSettings(request.get_json(force=True, silent=True))
            except ValueError as e:
                return Response(json.dumps({"error": str(e)}), status=400, mimetype="application/json")

            old_raw = stream_settings["raw"]
            stream_settings.update(updated)
            if updated["raw"]["size"] != old_raw["size"]:
                # The lores stream size can only change with the camera stopped
                restart_camera()
            elif updated["raw"]["fps"] != old_raw["fps"]:
                picam2.set_controls({"FrameDurationLimits": frameDuration(updated["raw"]["fps"])})
            save_stream_settings()

    return Response(json.dumps(stream_settings), mimetype="application/json")

# Cropped stream: one producer thread shared by all viewers,
# only running while at least one viewer is connected
crop_output = StreamingOutput()
crop_lock = Lock()
crop_viewers = 0
crop_thread = None

def api_config_video():
    global saved_box_points

    with camera_lock:
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

    with camera_lock:
        for i in range(5):
            im = picam2.capture_array()

    # Make it easier to process
    rotated = cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)
    gray = cv2.cvtColor(rotated, cv2.COLOR_RGB2GRAY)

    if len(saved_box_points) == 0:
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
    return render_template('stream.html', style="crop", settings=stream_settings,
                           sizes=crop_sizes, max_fps=max_fps)

def video_feed():
    video_config_filepath = get_video_config_filepath()
    return Response(gen_frames(style = "crop",
                               video_config = video_config_filepath),
                               mimetype='multipart/x-mixed-replace; boundary=frame')

# Raw video
def raw_stream():
    return render_template('stream.html', style="raw", settings=stream_settings,
                           sizes=raw_sizes, max_fps=max_fps)

def raw_video_feed():
    video_config_filepath = get_video_config_filepath()
    return Response(gen_frames(style = "raw",
                               mouse_config = "",
                               video_config = video_config_filepath),
                               mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames(style = "crop", mouse_config="", video_config=""):
    global crop_viewers, crop_thread

    if style == "raw":
        # Already JPEG encoded by the hardware encoder, the browser rotates it
        while True:
            with output.condition:
                output.condition.wait()
                frame = output.frame
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    with crop_lock:
        crop_viewers += 1
        if crop_thread is None:
            crop_thread = Thread(target=crop_frames, daemon=True)
            crop_thread.start()
    try:
        while True:
            with crop_output.condition:
                # Time out and resend the last frame, so a stalled stream
                # still notices when the browser goes away
                crop_output.condition.wait(timeout=1)
                frame = crop_output.frame
            if frame is None:
                continue
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        with crop_lock:
            crop_viewers -= 1

def crop_frames():
    global crop_thread
    box = None
    found_box = [None] # Set by the screen finder thread
    finder = None
    last_check = 0
    next_frame = time.monotonic()

    while True:
        with crop_lock:
            if crop_viewers == 0:
                crop_thread = None
                return

        settings = stream_settings["crop"]
        width, height = crop_sizes[settings["size"]]
        refPoints = np.array([(0,0),(width,0),(width,height),(0,height)], dtype="float32")

        now = time.monotonic()
        if next_frame > now:
            time.sleep(next_frame - now)
        next_frame = max(next_frame, now) + 1 / settings["fps"]

        if len(saved_box_points) > 0:
            box = saved_box_points
        elif found_box[0] is not None:
            box = found_box[0]

        gray = None
        warp = None
        camera_lock.acquire()
        request = picam2.capture_request()
        try:
            # Work on the camera buffer directly instead of copying the frame
            with MappedArray(request, "main") as m:
                im = m.array
                if len(saved_box_points) == 0 and (finder is None or not finder.is_alive()) and \
                   time.monotonic() - last_check >= screen_check_interval:
                    gray = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)
                if box is not None:
                    # The 90° counterclockwise rotation is folded into the transform
                    transform = cv2.getPerspectiveTransform(unrotatePoints(box, im.shape[1]), refPoints)
                    warp = cv2.warpPerspective(im, transform, (width, height))
        finally:
            request.release()
            camera_lock.release()

        if gray is not None:
            # Look for the screen in the background so the stream doesn't stall
            last_check = time.monotonic()
            finder = Thread(target=findScreen, args=(gray, found_box), daemon=True)
            finder.start()

        if warp is None:
            continue

        alpha = 1.3 # Contrast control (1.0-3.0)
        beta = 30 # Brightness control (0-100)
        adjusted = cv2.convertScaleAbs(warp, alpha=alpha, beta=beta)

        if settings["gray"]:
            adjusted = cv2.cvtColor(adjusted, cv2.COLOR_RGB2GRAY)

        success, buffer = cv2.imencode('.jpg', adjusted)
        crop_output.write(buffer.tobytes())
