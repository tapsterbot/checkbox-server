import json
from flask import request, Response

from zero_hid import Keyboard, KeyCodes

# Set up keyboard
k = Keyboard()

def api_keyboard_type():
    req = request.json
    text = req.get("text")
    print("Keyboard type text: %s" % text)
    k.type(text)
    return Response(mimetype="application/json")

def api_keyboard_press():
    req = request.json
    modifiers = req.get("modifiers")
    key = req.get("key")
    print("Keyboard press modifiers: %s" % modifiers)
    print("Keyboard press key: %s" % key)
    k.press(modifiers, key)
    return Response(mimetype="application/json")

######################################################################
#
# Websocket Keyboard
#
######################################################################
def handle_keyboard_websocket_message(ws):
    print("yo, keyboard socket")
    while True:
        data = ws.receive()
        print('received message: ' + str(data))
        try:
            json_data = json.loads(data)
            if json_data.get('type') == "upArrow":
                print("upArrow!")
                k.press([],0x52)
                k.press([],0x52)
            if json_data.get('type') == "downArrow":
                print("downArrow!")
                k.press([],0x51)
                k.press([],0x51)
        except Exception:
            pass

