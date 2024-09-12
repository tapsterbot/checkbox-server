# To run:
# $ python server.py
# or
# $ gunicorn 'server:app' --bind=0.0.0.0:5000 --workers=1 --threads=2 --timeout=0

# TODO
# Video Config wizard
# X - Get portrait rect
# X - Get landscape rect
# X - Use config when starting server
# X - Write video config to file
# Mouse Config wizard
# - Write mouse config to file

# Mouse
# X press
# X release
# X origin
# X click
# - swipe up
# - swipe down
# - swipe left
# - swipe right

# Keyboard
# X type
# X type with keys
# X key press
# X key release

import time
import json
import mapper
import numpy as np
from zero_hid import Mouse
from flask import Flask, request, render_template, Response
from flask_sock import Sock

from routes import index, config, mouse, keyboard, touch
import uuid
import os

# TODO: Use output from "libcamera-hello --list-cameras" instead of requiring a flag
import argparse
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('--video', help="video source: camera or hdmi\n" + \
                                    "example:\n" + \
                                    "  python server.py --video=camera\n" + \
                                    "  python server.py --video=hdmi\n\n")

args = parser.parse_args()

if args.video:
    video_source = args.video
else:
    video_source = "hdmi"

if video_source == "hdmi":
    os.system('echo "1. Setting edid..."')
    os.system('v4l2-ctl --set-edid=file=video-driver/1080p30edid --fix-edid-checksums')
    #os.system('v4l2-ctl --set-edid=file=video-driver/720p60edid --fix-edid-checksums')
    os.system('sleep 10')

    os.system('echo "2. Setting digital video timings..."')
    os.system('v4l2-ctl --set-dv-bt-timings query')
    os.system('sleep 4')

    os.system('echo "3. Querying digital video timings..."')
    os.system('v4l2-ctl --query-dv-timings')
    os.system('sleep 4')

    os.system('echo "4. Setting pixel format..."')
    os.system('v4l2-ctl -v pixelformat=UYVY')
    os.system('sleep 1')

    os.system('echo "Done with video set-up."')

    from routes import video_hdmi as video


elif video_source == "camera":
    from routes import video_camera as video


app = Flask(__name__)
app.config['SECRET_KEY'] = uuid.uuid4().hex
app.url_map.strict_slashes = False
#socketio = SocketIO(app)
sock = Sock(app)

# Set up temp mouse data
app.last_mouse_click = {"x": None, "y": None}

# Video config location
app.video_config_filepath = "config/video-config.json"

# Load mouse config
app.mouse_config_filepath = "config/mouse-config.json"
app.transformationMatrix = np.zeros(0)
mouse_config_file = open(app.mouse_config_filepath)
mouse_config_data = json.load(mouse_config_file)
if mouse_config_data.get("configured") == False:
    print("Mouse not configured yet!")
else:
    app.transformationMatrix = mapper.getTransformationMatrix(mouse_config_data)
    print(app.transformationMatrix)

# Routes
# Index
app.add_url_rule('/', view_func=index.index)

# Ping
@app.route('/api/ping')
def api_ping():
    text = '"pong"'
    return Response(response=text, status=200, mimetype="application/json")

# Config Routes
app.add_url_rule('/config/blank', view_func=config.blank)
#app.add_url_rule('/config/click', view_func=config.click)
#app.add_url_rule('/api/config/mouse/click', view_func=config.api_config_mouse_click, methods=['POST'])
#app.add_url_rule('/api/config/mouse/last-click', view_func=config.api_config_mouse_last_click)
if video_source == "hdmi":
    app.add_url_rule('/api/config/mouse/start', view_func=video.api_start_mouse_config, methods=['POST'])
    app.add_url_rule('/api/config/mouse/position', view_func=video.api_config_get_mouse_position)
    app.add_url_rule('/api/config/mouse/screen-position', view_func=video.api_config_get_mouse_screen_position)
    app.add_url_rule('/api/config/video/data', view_func=video.api_video_config_data, methods=['POST'])


# Mouse Routes
app.add_url_rule('/api/mouse/jiggle', view_func=mouse.api_mouse_jiggle)
app.add_url_rule('/api/mouse/down', view_func=mouse.api_mouse_down, methods=['POST'])
app.add_url_rule('/api/mouse/up', view_func=mouse.api_mouse_up, methods=['POST'])
app.add_url_rule('/api/mouse/click', view_func=mouse.api_mouse_click, methods=['POST'])
app.add_url_rule('/api/mouse/move/by', view_func=mouse.api_mouse_move_by, methods=['POST'])
app.add_url_rule('/api/mouse/move/home', view_func=mouse.api_mouse_move_home, methods=['POST'])
app.add_url_rule('/api/raw/mouse/drag/by', view_func=mouse.api_raw_mouse_drag_by, methods=['POST'])
app.add_url_rule('/api/raw/mouse/swipe/up', view_func=mouse.api_raw_mouse_swipe_up, methods=['POST'])
app.add_url_rule('/api/raw/mouse/swipe/down', view_func=mouse.api_raw_mouse_swipe_down, methods=['POST'])
app.add_url_rule('/api/raw/mouse/swipe/left', view_func=mouse.api_raw_mouse_swipe_left, methods=['POST'])
app.add_url_rule('/api/raw/mouse/swipe/right', view_func=mouse.api_raw_mouse_swipe_right, methods=['POST'])
app.add_url_rule('/api/raw/mouse/move/by', view_func=mouse.api_raw_mouse_move_by, methods=['POST'])

# MouseKeys Routes
app.add_url_rule('/api/mouse-keys/jiggle', view_func=mouse.api_mouse_keys_jiggle)
app.add_url_rule('/api/mouse-keys/down', view_func=mouse.api_mouse_keys_down, methods=['POST'])
app.add_url_rule('/api/mouse-keys/up', view_func=mouse.api_mouse_keys_up, methods=['POST'])
app.add_url_rule('/api/mouse-keys/click', view_func=mouse.api_mouse_keys_click, methods=['POST'])
app.add_url_rule('/api/mouse-keys/move/to', view_func=mouse.api_mouse_keys_move_to, methods=['POST'])
app.add_url_rule('/api/mouse-keys/move/home', view_func=mouse.api_mouse_keys_move_home, methods=['POST'])
app.add_url_rule('/api/raw/mouse-keys/drag/by', view_func=mouse.api_raw_mouse_keys_drag_by, methods=['POST'])
app.add_url_rule('/api/raw/mouse-keys/move/by', view_func=mouse.api_raw_mouse_keys_move_by, methods=['POST'])

# Keyboard Routes
app.add_url_rule('/api/keyboard/type', view_func=keyboard.api_keyboard_type, methods=['POST'])
app.add_url_rule('/api/keyboard/press', view_func=keyboard.api_keyboard_press, methods=['POST'])

# Touch Routes
app.add_url_rule('/api/touch/tap', view_func=touch.api_touch_tap, methods=['POST'])
app.add_url_rule('/api/touch/move', view_func=touch.api_touch_move, methods=['POST'])

# Video Routes
if video_source == "hdmi":
    app.add_url_rule('/stream', view_func=video.stream)
    app.add_url_rule('/video-feed', view_func=video.video_feed)

    app.add_url_rule('/raw/stream', view_func=video.raw_stream)
    app.add_url_rule('/raw/video-feed', view_func=video.raw_video_feed)

    app.add_url_rule('/config/video', view_func=video.config_video)
    app.add_url_rule('/config/video-feed', view_func=video.config_video_feed)

    app.add_url_rule('/config/mouse', view_func=video.config_mouse)
    app.add_url_rule('/config/mouse-feed', view_func=video.config_mouse_feed)

    app.add_url_rule('/screenshot', view_func=video.api_screenshot)
    app.add_url_rule('/api/screenshot', view_func=video.api_screenshot)

if video_source == "camera":
    app.add_url_rule('/screenshot', view_func=video.api_screenshot)
    app.add_url_rule('/api/screenshot', view_func=video.api_screenshot)
    app.add_url_rule('/screenshot/gray', view_func=video.api_screenshot)
    app.add_url_rule('/api/screenshot/gray', view_func=video.api_screenshot)
    app.add_url_rule('/stream', view_func=video.stream)
    app.add_url_rule('/video-feed', view_func=video.video_feed)
    app.add_url_rule('/raw/stream', view_func=video.raw_stream)
    app.add_url_rule('/raw/video-feed', view_func=video.raw_video_feed)
    app.add_url_rule('/api/config/video/camera', view_func=video.api_config_video, methods=['POST'])

# WebSocket config
sock.route('/socket')(mouse.handle_websocket_message)
sock.route('/keyboard')(keyboard.handle_keyboard_websocket_message)


if __name__ == '__main__':
    # Debug/Development
    app.run(debug=False, host="0.0.0.0", port="5000")
