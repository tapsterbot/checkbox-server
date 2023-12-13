import cv2
import numpy as np
from flask import current_app, render_template, Response
import sys
import os
import json
import datetime

print("Video mode: HDMI")

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
last_mouse_screen_position = {"x": None, "y": None}

# Set up camera
camera = cv2.VideoCapture(0)
#camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
#camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

if not (camera.isOpened()):
    print("Could not open video device")

def api_screenshot():
    video_config_filepath = get_video_config_filepath()
    last_modified = os.path.getmtime(video_config_filepath)
    video_config_file = open(video_config_filepath)
    video_config_data = json.load(video_config_file)
    #print("Video Config Filepath: ", video_config_filepath)
    #print("Last modified: %s" % last_modified)
    #print("Video Config Data: ", video_config_data)

    # Need to flush the buffer of old frames from the video capture card
    for i in range(5):
        success, frame = camera.read()

    frame2 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame3 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(frame3,1,255,cv2.THRESH_BINARY)
    br_x, br_y, br_w, br_h = cv2.boundingRect(thresh)

    if br_h > br_w: # Vertical
        if video_config_data['vertical']['configured'] == True:
            vert = video_config_data.get('vertical')
            x = vert.get('x')
            y = vert.get('y')
            w = vert.get('w')
            h = vert.get('h')
            frame4 = frame2[y:y+h, x:x+w]
        else: # configured == False:
            frame4 = frame2
    else: # Horizontal
        if video_config_data['horizontal']['configured'] == True:
            horiz = video_config_data.get('horizontal')
            x = horiz.get('x')
            y = horiz.get('y')
            w = horiz.get('w')
            h = horiz.get('h')
            frame4 = frame2[y:y+h, x:x+w]
        else: # configured == False:
            frame4 = frame2

    success, buffer = cv2.imencode('.jpg', frame4)

    response = Response(buffer.tobytes(), mimetype='image/jpeg')
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

# Config video
def config_video():
    return render_template('config-video-stream.html')

def config_video_feed():
    mouse_config_filepath = get_mouse_config_filepath()
    video_config_filepath = get_video_config_filepath()
    return Response(gen_frames(style = "video-config",
                               mouse_config = mouse_config_filepath,
                               video_config = video_config_filepath),
                               mimetype='multipart/x-mixed-replace; boundary=frame')

# Config mouse
def config_mouse():
    return render_template('config-mouse-stream.html')

def config_mouse_feed():
    mouse_config_filepath = get_mouse_config_filepath()
    video_config_filepath = get_video_config_filepath()
    return Response(gen_frames(style = "mouse-config",
                               mouse_config = mouse_config_filepath,
                               video_config = video_config_filepath),
                               mimetype='multipart/x-mixed-replace; boundary=frame')

# Request comes in here via config-mouse-stream.html
def api_start_mouse_config():
    global last_mouse_screen_position
    print("Start Mouse Config!")
    #req = request.json
    #x_pos = req.get("x")
    #y_pos = req.get("y")
    #print("Mouse Config Click: (%s, %s)" % (x_pos, y_pos))
    return Response(mimetype="application/json")

def api_config_get_mouse_position():
    print("TODO: Mouse Position")
    data = {"x": None,
            "y": None}
    return Response(mimetype="application/json", response = json.dumps(data))

def api_config_get_mouse_screen_position():
    global last_mouse_screen_position
    print("Mouse Screen Position: (%s, %s)" % (last_mouse_screen_position["x"], last_mouse_screen_position["y"]))
    data = {"x": last_mouse_screen_position["x"],
            "y": last_mouse_screen_position["y"]}
    return Response(mimetype="application/json", response = json.dumps(data))

def api_video_config_data():
    print("Saving video data...")
    video_config_filepath = get_video_config_filepath()
    last_modified = os.path.getmtime(video_config_filepath)
    video_config_file = open(video_config_filepath,'r')
    video_config_data = json.load(video_config_file)
    video_config_file.close()
    #print("Video Config Filepath: ", video_config_filepath)
    #print("Current video Config: ", video_config_data)
    #print("Last modified: %s" % last_modified)
    #print("Last video size: %s" % last_video_size)

    if last_video_size.get("o") == "v":
        video_config_data["vertical"]["configured"] = True
        video_config_data["vertical"]["timestamp"] = datetime.datetime.now(datetime.UTC).isoformat()
        video_config_data["vertical"]["x"] = last_video_size.get("x")
        video_config_data["vertical"]["y"] = last_video_size.get("y")
        video_config_data["vertical"]["w"] = last_video_size.get("w")
        video_config_data["vertical"]["h"] = last_video_size.get("h")
    elif last_video_size.get("o") == "h":
        video_config_data["horizontal"]["configured"] = True
        video_config_data["horizontal"]["timestamp"] = datetime.datetime.now(datetime.UTC).isoformat()
        video_config_data["horizontal"]["x"] = last_video_size.get("x")
        video_config_data["horizontal"]["y"] = last_video_size.get("y")
        video_config_data["horizontal"]["w"] = last_video_size.get("w")
        video_config_data["horizontal"]["h"] = last_video_size.get("h")

    print("New Video Config: ", video_config_data )
    new_video_config_json = json.dumps(video_config_data, indent=2)
    video_config_file = open(video_config_filepath,'w')
    video_config_file.write(new_video_config_json)
    video_config_file.close()

    return Response(mimetype="application/json")


def gen_frames(style = "crop", mouse_config="", video_config=""):
    global last_video_size
    global last_mouse_screen_position
    print("Video Config: ", video_config)
    last_modified = os.path.getmtime(video_config)
    #print("Last modified: %s" % last_modified)
    video_config_file = open(video_config)
    video_config_data = json.load(video_config_file)
    #print("Video Config Data:")
    #print(video_config_data)

    while True:
        success, frame = camera.read()  # read the camera frame

        if not success:
            break
        else:
            if style == "crop":
                frame2 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame3 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(frame3,1,255,cv2.THRESH_BINARY)
                br_x, br_y, br_w, br_h = cv2.boundingRect(thresh)

                if br_h > br_w: # Vertical
                    if video_config_data['vertical']['configured'] == True:
                        vert = video_config_data.get('vertical')
                        x = vert.get('x')
                        y = vert.get('y')
                        w = vert.get('w')
                        h = vert.get('h')
                        frame4 = frame2[y:y+h, x:x+w]
                    else: # configured == False:
                        frame4 = frame2

                else: # Horizontal
                    if video_config_data['vertical']['configured'] == True:
                        horiz = video_config_data.get('horizontal')
                        x = horiz.get('x')
                        y = horiz.get('y')
                        w = horiz.get('w')
                        h = horiz.get('h')
                        frame4 = frame2[y:y+h, x:x+w]
                    else: # configured == False:
                        frame4 = frame2

                success, buffer = cv2.imencode('.jpg', frame4)
                frame5 = buffer.tobytes()
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame5 + b'\r\n')

            elif style == "raw":
                success, buffer = cv2.imencode('.jpg', frame)
                frame2 = buffer.tobytes()
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame2 + b'\r\n')

            elif style == "video-config":
                frame2 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame3 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(frame3,1,255,cv2.THRESH_BINARY)
                br_x, br_y, br_w, br_h = cv2.boundingRect(thresh)

                if br_h > br_w: # Vertical
                    orientation = "v"
                else:
                    orientation = "h"
                text_color = (127, 127, 127)
                if br_h > br_w: # Vertical
                    if video_config_data['vertical']['configured'] == True:
                        vert = video_config_data.get('vertical')
                        x = vert.get('x')
                        y = vert.get('y')
                        w = vert.get('w')
                        h = vert.get('h')

                        if ( (x == br_x) and (y == br_y) and (w == br_w) and (h == br_h) ):
                            text_color = (256, 0, 0)
                        else:
                            pass

                else: # Horizontal
                    if video_config_data['vertical']['configured'] == True:
                        horiz = video_config_data.get('horizontal')
                        x = horiz.get('x')
                        y = horiz.get('y')
                        w = horiz.get('w')
                        h = horiz.get('h')

                        if ( (x == br_x) and (y == br_y) and (w == br_w) and (h == br_h) ):
                            text_color = (256, 0, 0)
                        else:
                            pass



                #print(last_video_size)
                last_video_size = {"o": orientation, "x":br_x, "y":br_y, "w": br_w, "h":br_h}
                #print(last_video_size)

                # Draw outline around frame
                cv2.rectangle(frame2, (br_x, br_y), (br_x + br_w, br_y + br_h), (0, 255, 0), 4)

                # Put info on frame
                text_x = 50
                #text_y = 40
                text_y = int( ((br_h - br_y)/2)  + br_y - 62.5 )

                if br_h > br_w:
                    mode = "vertical"
                else:
                    mode = "horizontal"
                cv2.putText(frame2, 'O: %s' % mode, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2, cv2.LINE_AA)
                cv2.putText(frame2, 'X: %s' % br_x, (text_x, text_y+35*1), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2, cv2.LINE_AA)
                cv2.putText(frame2, 'Y: %s' % br_y, (text_x, text_y+35*2), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2, cv2.LINE_AA)
                cv2.putText(frame2, 'W: %s' % br_w, (text_x, text_y+35*3), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2, cv2.LINE_AA)
                cv2.putText(frame2, 'H: %s' % br_h, (text_x, text_y+35*4), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2, cv2.LINE_AA)

                success, buffer = cv2.imencode('.jpg', frame2)
                frame2 = buffer.tobytes()
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame2 + b'\r\n')

            elif style == "mouse-config":
                frame2 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame3 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(frame3,1,255,cv2.THRESH_BINARY)
                br_x, br_y, br_w, br_h = cv2.boundingRect(thresh)

                if br_h > br_w: # Vertical
                    if video_config_data['vertical']['configured'] == True:
                        vert = video_config_data.get('vertical')
                        x = vert.get('x')
                        y = vert.get('y')
                        w = vert.get('w')
                        h = vert.get('h')
                        frame4 = frame2[y:y+h, x:x+w]
                    else: # configured == False:
                        frame4 = frame2
                    # Draw outline around frame
                    cv2.rectangle(frame4, (0, 0), (frame4.shape[1], frame4.shape[0]), (0, 255, 0), 4)

                else: # Horizontal
                    if video_config_data['horizontal']['configured'] == True:
                        horiz = video_config_data.get('horizontal')
                        x = horiz.get('x')
                        y = horiz.get('y')
                        w = horiz.get('w')
                        h = horiz.get('h')
                        frame4 = frame2[y:y+h, x:x+w]
                    else: # configured == False:
                        frame4 = frame2
                    # Draw outline around frame
                    cv2.rectangle(frame4, (0, 0), (frame4.shape[1], frame4.shape[0]), (0, 255, 0), 4)
                #print(frame4.shape)

                frame_circles = frame4
                frame_circles = cv2.cvtColor(frame4, cv2.COLOR_BGR2GRAY)
                frame_circles2 = cv2.medianBlur(frame_circles, 5)
                circles = cv2.HoughCircles(frame_circles2, cv2.HOUGH_GRADIENT, 1, minDist=50, param1=50, param2=30, minRadius=30, maxRadius=110)

                if circles is not None:
                    # Convert the coordinates & radius to integers
                    circles = np.round(circles[0, :]).astype("int")

                    for (x, y, r) in circles:
                        if (y > 0) & (y < (frame4.shape[0] - 100)):
                            #print(x, y, r)
                            last_mouse_screen_position["x"] = int(x)
                            last_mouse_screen_position["y"] = int(y)
                            cv2.circle(frame4, (x, y), r, (255, 0, 0), 3)

                success, buffer = cv2.imencode('.jpg', frame4)
                frame5 = buffer.tobytes()
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame5 + b'\r\n')