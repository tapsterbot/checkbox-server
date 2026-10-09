import socket
from flask import current_app, render_template

# Descriptions for the API explorer, in the order they're shown.
# Only routes the server actually has (camera or HDMI mode) are listed,
# and any route missing from here still shows up under "Other".
sections = [
    ("Video", [
        ("/stream", "Live phone screen, cropped and straightened. "
                    "Click the video to control the phone with the mouse, Esc to let go.", None),
        ("/raw/stream", "Live view of the whole camera or HDMI image.", None),
        ("/video-feed", "MJPEG stream behind /stream, for an <img> tag or a video player.", None),
        ("/raw/video-feed", "MJPEG stream behind /raw/stream.", None),
        ("/screenshot", "PNG of the phone screen at full resolution.", None),
        ("/api/screenshot", "Same as /screenshot.", None),
        ("/screenshot/gray", "Grayscale PNG of the phone screen.", None),
        ("/api/screenshot/gray", "Same as /screenshot/gray.", None),
    ]),
    ("Touch", [
        ("/api/touch/tap", "Tap a point. x and y are percent of the screen, 0 to 100.",
         '{"x": 50, "y": 50}'),
        ("/api/touch/move", "Drag from one point to another, in percent of the screen.",
         '{"x1": 50, "y1": 80, "x2": 50, "y2": 20}'),
    ]),
    ("Keyboard", [
        ("/api/keyboard/type", "Type some text.", '{"text": "hello"}'),
        ("/api/keyboard/press", "Press one key. key is a USB HID key code (40 is Enter), "
                                "modifiers a list of modifier codes.",
         '{"modifiers": [0], "key": 40}'),
    ]),
    ("Mouse", [
        ("/api/mouse/click", "Click.", None),
        ("/api/mouse/down", "Press the button.", None),
        ("/api/mouse/up", "Release the button.", None),
        ("/api/mouse/move/by", "Move by x, y.", '{"x": 100, "y": 0}'),
        ("/api/mouse/move/home", "Move to the top left corner.", None),
        ("/api/mouse/jiggle", "Move a little and back, to wake the pointer.", None),
        ("/api/raw/mouse/move/by", "Move by x, y in raw mouse units.", '{"x": 100, "y": 0}'),
        ("/api/raw/mouse/drag/by", "Move by x, y with the button held.", '{"x": 0, "y": -100}'),
        ("/api/raw/mouse/swipe/up", "Swipe up.", None),
        ("/api/raw/mouse/swipe/down", "Swipe down.", None),
        ("/api/raw/mouse/swipe/left", "Swipe left.", None),
        ("/api/raw/mouse/swipe/right", "Swipe right.", None),
    ]),
    ("Mouse keys", [
        ("/api/mouse-keys/click", "Click, using the keypad mouse keys.", None),
        ("/api/mouse-keys/down", "Press the button.", None),
        ("/api/mouse-keys/up", "Release the button.", None),
        ("/api/mouse-keys/move/to", "Move to x, y on the screen, using the mouse config.",
         '{"x": 100, "y": 200}'),
        ("/api/mouse-keys/move/home", "Move to the top left corner.", None),
        ("/api/mouse-keys/jiggle", "Move a little and back.", None),
        ("/api/raw/mouse-keys/move/by", "Move by x, y.", '{"x": 10, "y": 0}'),
        ("/api/raw/mouse-keys/drag/by", "Move by x, y.", '{"x": 0, "y": -10}'),
    ]),
    ("Setup", [
        ("/api/config/stream", "Stream settings shared by every viewer: fps, size, gray. "
                               "Saved to config/video-config.json.",
         '{"crop": {"fps": 5, "size": "small", "gray": true}}'),
        ("/api/config/video/camera", "Find the phone screen in the camera image, "
                                     "and use that box for /stream and screenshots until restart.", None),
        ("/config/video", "Video crop setup.", None),
        ("/config/video-feed", "MJPEG stream behind /config/video.", None),
        ("/api/config/video/data", "Save the video crop, used by /config/video.", None),
        ("/config/mouse", "Mouse setup.", None),
        ("/config/mouse-feed", "MJPEG stream behind /config/mouse.", None),
        ("/api/config/mouse/start", "Used by /config/mouse.", None),
        ("/api/config/mouse/position", "Used by /config/mouse.", None),
        ("/api/config/mouse/screen-position", "Used by /config/mouse.", None),
        ("/config/blank", "Blank page for setup and testing.", None),
    ]),
    ("WebSockets", [
        ("/socket", "Mouse events from the stream page.", None),
        ("/keyboard", "Arrow keys from the stream page.", None),
    ]),
    ("Server", [
        ("/explorer", "Try the API from the browser.", None),
        ("/api/ping", "Returns \"pong\".", None),
    ]),
]

websockets = ["/socket", "/keyboard"]

def available_sections():
    # What the server actually has, with the methods each route takes
    routes = {}
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint == "static" or rule.rule == "/":
            continue
        methods = sorted(rule.methods - {"HEAD", "OPTIONS"})
        if rule.rule in websockets:
            methods = ["WS"]
        routes[rule.rule] = methods

    listed = []
    shown = set()
    for title, entries in sections:
        rows = []
        for path, description, example in entries:
            if path in routes:
                rows.append({"path": path, "methods": routes[path],
                             "description": description, "example": example})
                shown.add(path)
        if rows:
            listed.append((title, rows))

    other = [{"path": path, "methods": methods, "description": "", "example": None}
             for path, methods in sorted(routes.items()) if path not in shown]
    if other:
        listed.append(("Other", other))
    return listed

def index():
    return render_template('index.html', hostname=socket.gethostname(),
                           video_source=current_app.video_source)

def explorer():
    return render_template('explorer.html', sections=available_sections(),
                           hostname=socket.gethostname(),
                           video_source=current_app.video_source)
