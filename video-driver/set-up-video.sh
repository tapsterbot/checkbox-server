echo "1. Setting edid..."
v4l2-ctl --set-edid=file=1080p30edid --fix-edid-checksums
sleep 10

echo "2. Setting digital video timings..."
# Success:
# BT timings set
#
# Failure:
# VIDIOC_QUERY_DV_TIMINGS: failed: Link has been severed
# or
# ... Especially if web server is still running:
# VIDIOC_S_DV_TIMINGS: failed: Device or resource busy
v4l2-ctl --set-dv-bt-timings query
sleep 4

echo "3. Querying digital video timings..."
# Success:
# ...
#        Active width: 1280
#        Active height: 720
# ...
# Failure:
# VIDIOC_QUERY_DV_TIMINGS: failed: Link has been severed
#        Active width: 0
#        Active height: 0
# ...
v4l2-ctl --query-dv-timings
sleep 4

echo "4. Setting pixel format..."
# Failure:
# VIDIOC_S_FMT: failed: Device or resource busy
v4l2-ctl -v pixelformat=UYVY

echo "Done."


# Check for errors
# v4l2-ctl --log-status
