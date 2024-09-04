from flask import request, Response
from zero_hid import Touch

# Set up touch
t = Touch()

######################################################################
#
# Touch
#
######################################################################
def api_touch_tap():
    req = request.json
    x_pos = req.get("x")
    y_pos = req.get("y")
    print("Touch Tap: (%s, %s)" % (x_pos, y_pos))
    t.tap(x_pos, y_pos)
    return Response(mimetype="application/json")

def api_touch_move():
    req = request.json
    x1_pos = req.get("x1")
    y1_pos = req.get("y1")
    x2_pos = req.get("x2")
    y2_pos = req.get("y2")
    print("Touch Move: (%s, %s) to (%s, %s)" % (x1_pos, y1_pos, x2_pos, y2_pos))
    t.move(x1_pos, y1_pos, x2_pos, y2_pos, points = 5, delay = .1)
    return Response(mimetype="application/json")