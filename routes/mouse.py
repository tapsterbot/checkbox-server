import time
import os
import sys
import numpy as np
import mapper
from flask import current_app, request, Response
from zero_hid import Mouse
from zero_hid.hid.mouse import send_mouse_event
from zero_hid import Keyboard, KeyCodes
from zero_hid.hid.keyboard import send_keystroke

# Set up mouse
m = Mouse()

last_x_pos = -100
last_y_pos = -100

# # Config helper functions
# def app_file_path():
#     # Get the app filepath
#     fn = getattr(sys.modules['__main__'], '__file__')
#     root_path = os.path.abspath(os.path.dirname(fn))
#     return root_path

# def get_mouse_config_filepath():
#     mouse_filepath = os.path.join(app_file_path(), current_app.mouse_config_fie)
#     return mouse_filepath

# transformationMatrix = np.zeros(0)
# mouse_config_filepath = get_mouse_config_filepath()
# mouse_config_file = open(mouse_config_filepath)
# mouse_config_data = json.load(mouse_config_file)
# transformationMatrix = mapper.getTransformationMatrix(mouse_config_data)
# print(transformationMatrix)

######################################################################
#
# Mouse
#
######################################################################
def api_mouse_jiggle():
    m.move_relative(10,0)
    time.sleep(.5)
    m.move_relative(-10,0)
    return Response()

def api_mouse_down():
    print("Mouse down")
    send_mouse_event('/dev/hidg1', 0x1, 0, 0, 0, 0)
    return Response()

def api_mouse_up():
    print("Mouse up")
    send_mouse_event('/dev/hidg1', 0x0, 0, 0, 0, 0)
    return Response()

def api_mouse_click():
    print("Mouse click")
    send_mouse_event('/dev/hidg1', 0x1, 0, 0, 0, 0)
    time.sleep(.05)
    send_mouse_event('/dev/hidg1', 0x0, 0, 0, 0, 0)
    return Response()

def api_mouse_move_by():
    req = request.json
    x_pos = req.get("x")
    y_pos = req.get("y")
    print("Mouse move: (%s, %s)" % (x_pos, y_pos))
    mouse_move_by(x_pos, y_pos)
    return Response(mimetype="application/json")

def api_mouse_move_home():
    print("Mouse move home")
    mouse_move_by(-1500, -2500)
    mouse_move_by(0, 40)
    mouse_move_by(-100, 0)
    mouse_move_by(40, 0)
    mouse_move_by(0, -100)
    mouse_move_by(0, 40)
    return Response(mimetype="application/json")

def api_raw_mouse_drag_by():
    req = request.json
    x_pos = req.get("x")
    y_pos = req.get("y")
    print("Mouse drag: (%s, %s)" % (x_pos, y_pos))
    send_mouse_event('/dev/hidg1', 0x1, x_pos, y_pos, 0, 0)
    return Response(mimetype="application/json")

def api_raw_mouse_move_by():
    req = request.json
    x_pos = req.get("x")
    y_pos = req.get("y")
    print("Raw mouse move: (%s, %s)" % (x_pos, y_pos))
    mouse_move_by(x_pos, y_pos)
    return Response(mimetype="application/json")

def mouse_move_by(x, y, transform = False):
    delta = 125
    x_pos, y_pos = int(round(x)), int(round(y))

    if not -delta < x_pos < delta:
        if x_pos < -delta:
            while x_pos < -delta:
                m.move_relative(-delta, 0)
                x_pos += delta

        if x_pos > delta:
            while x_pos > delta:
                m.move_relative(delta, 0)
                x_pos -= delta

    if not -delta < y_pos < delta:
        if y_pos < -delta:
            while y_pos < -delta:
                m.move_relative(0, -delta)
                y_pos += delta

        if y_pos > delta:
            while y_pos > delta:
                m.move_relative(0, delta)
                y_pos -= delta

    m.move_relative(x_pos, y_pos)

######################################################################
#
# Mouse Keys
#
######################################################################
def api_mouse_keys_jiggle():
    send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KP4)
    time.sleep(.5)
    send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KP6)
    return Response()

def api_mouse_keys_down():
    print("Mouse keys down")
    send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KP0)
    return Response()

def api_mouse_keys_up():
    print("Mouse keys up")
    send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KPDOT)
    return Response()

def api_mouse_keys_click():
    print("Mouse keys click")
    send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KP5)
    return Response()

def api_mouse_keys_move_to():
    global last_x_pos
    global last_y_pos
    req = request.json
    x_pos = int(req.get("x"))
    y_pos = int(req.get("y"))
    x_pos, y_pos = mapper.transformPoint(x_pos, y_pos, current_app.transformationMatrix)
    print("Mouse keys move: (%s, %s)" % (x_pos, y_pos))
    if (last_x_pos > -100 and last_y_pos > -100):
        mouse_keys_move_by(x_pos - last_x_pos, y_pos - last_y_pos)
    else:
        mouse_move_by(-1500, -2000)
        mouse_keys_move_by(0, 4)
        mouse_keys_move_by(-10, 0)
        mouse_keys_move_by(4, 0)
        mouse_keys_move_by(0, -10)
        mouse_keys_move_by(0, 4)
        mouse_keys_move_by(x_pos, y_pos)

    last_x_pos = x_pos
    last_y_pos = y_pos

    return Response(mimetype="application/json")

def api_mouse_keys_move_home():
    print("Mouse keys move home")
    mouse_move_by(-1500, -2000)
    mouse_keys_move_by(0, 3)
    mouse_keys_move_by(-10, 0)
    mouse_keys_move_by(3, 0)
    mouse_keys_move_by(0, -10)
    mouse_keys_move_by(0, 3)
    return Response(mimetype="application/json")

def api_raw_mouse_keys_drag_by():
    req = request.json
    x_pos = req.get("x")
    y_pos = req.get("y")
    print("Mouse keys drag: (%s, %s)" % (x_pos, y_pos))
    mouse_keys_move_by(x_pos, y_pos)
    return Response(mimetype="application/json")

def api_raw_mouse_keys_move_by():
    req = request.json
    x_pos = req.get("x")
    y_pos = req.get("y")
    print("Raw mouse keys move: (%s, %s)" % (x_pos, y_pos))
    mouse_keys_move_by(x_pos, y_pos)
    return Response(mimetype="application/json")

def mouse_keys_move_by(x, y, transform = False):
    x_pos, y_pos = int(round(x)), int(round(y))
    if transform == True:
        if current_app.transformationMatrix.any():
            x_pos, y_pos = mapper.transformPoint(x, y, current_app.transformationMatrix)
            print("Transform point to: (%s, %s)" % (x_pos, y_pos))

    while x_pos != 0 or y_pos != 0:

        if x_pos < 0 and y_pos < 0:
            send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KP7)
            x_pos += 1
            y_pos += 1

        elif x_pos < 0 and y_pos > 0:
            send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KP1)
            x_pos += 1
            y_pos -= 1

        elif x_pos < 0:
            send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KP4)
            x_pos += 1

        elif x_pos > 0 and y_pos < 0:
            send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KP9)
            x_pos -= 1
            y_pos += 1

        elif x_pos > 0 and y_pos > 0:
            send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KP3)
            x_pos -= 1
            y_pos -= 1

        elif x_pos > 0:
            send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KP6)
            x_pos -= 1

        elif y_pos < 0:
            send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KP8)
            y_pos += 1

        elif y_pos > 0:
            send_keystroke('/dev/hidg0', 0, KeyCodes.KEY_KP2)
            y_pos -= 1
