import numpy as np

"""
Map 2D Coordinates Routine

1. Connect phone to Checkbox
2. Using keyboard commands, open browser
3. Go to http://checkboxmini.local:5000/config/mouse

4. Find point #1
     - Move robot/mouse/pointer to first screen location
     - Read screen location
     - Store mouse and screen location as point #1

5. Find point #2
     - Move robot/mouse/pointer to first screen location
     - Read screen location
     - Store mouse and screen location as point #2

6. Write point data to disk
7. Read point data from disk

8. calcTransformationMatrix

# Point 1
>>> mk.home()
>>> mk.raw.move(10,10)
>>> c.mouse_screen_position()
# store screen x,y value in mouse-config.json

# Point 2
>>> mk.home()
>>> mk.raw.move(10,40)
>>> c.mouse_screen_position()
# store screen x,y value in mouse-config.json

"""

def getTransformationMatrix(config):
    """
    Based on "How to map points between 2D coordinate systems"
    https://msdn.microsoft.com/en-us/library/jj635757(v=vs.85).aspx

    However, it was modified to match the situation where both
    coordinate systems are the same and use a y-axis oriented downwards.

    More information, also check out:
    https://mathworld.wolfram.com/AffineTransformation.html
    """

    point1 = config["point1"]
    point2 = config["point2"]

    M = np.array([
        [ point1["screen"]["x"], -point1["screen"]["y"], 1, 0],
        [ point1["screen"]["y"], point1["screen"]["x"], 0, 1],
        [ point2["screen"]["x"], -point2["screen"]["y"], 1, 0],
        [ point2["screen"]["y"], point2["screen"]["x"], 0, 1]
    ])

    u = np.array([
        [point1["robot"]["x"]],
        [point1["robot"]["y"]],
        [point2["robot"]["x"]],
        [point2["robot"]["y"]]
    ])

    MI = np.linalg.inv(M)
    v = np.matmul(MI, u)

    return v

def transformPoint(x = 0, y = 0, transformationMatrix = np.zeros(0)):
    xprime = x
    yprime = y
    if transformationMatrix.any():
        v = transformationMatrix
        a = v[0,0]
        b = v[1,0]
        c = v[2,0]
        d = v[3,0]
        xprime = int(round( (a * x) - (b * y) + c ))
        yprime = int(round( (b * x) + (a * y) + d ))

    return (xprime, yprime)