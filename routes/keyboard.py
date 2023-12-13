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