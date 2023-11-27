import json
from flask import current_app, render_template, request, Response

def click():
    return render_template('click.html')

def blank():
    return render_template('blank.html')

# Data comes in here via clicks from click.html
def api_config_mouse_click():
    req = request.json
    x_pos = req.get("x")
    y_pos = req.get("y")
    print("Mouse Config Click: (%s, %s)" % (x_pos, y_pos))
    current_app.last_mouse_click["x"] = x_pos
    current_app.last_mouse_click["y"] = y_pos
    return Response(mimetype="application/json")

def api_config_mouse_last_click():
    print("Last Mouse Click: (%s, %s)" % (current_app.last_mouse_click["x"], current_app.last_mouse_click["y"]))
    data = {"x": current_app.last_mouse_click["x"],
            "y": current_app.last_mouse_click["y"]}
    return Response(mimetype="application/json", response = json.dumps(data))