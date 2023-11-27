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