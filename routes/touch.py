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
