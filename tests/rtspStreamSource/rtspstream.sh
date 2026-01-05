#!/bin/bash

# Configuration
CAMERA_DEVICE="/dev/video0"
PORT=8554

# Kill any existing streams
pkill -f "gst-launch-1.0"
pkill -f "gst-rtsp-server"

echo "Starting RTSP stream..."
echo "Stream will be available at: rtsp://$(hostname -I | awk '{print $1}'):${PORT}/stream"
echo "Or: rtsp://localhost:${PORT}/stream"

# Try different pipeline options

# Option 1: Simple pipeline with software encoding
gst-launch-1.0 -v \
    v4l2src device=${CAMERA_DEVICE} ! \
    videoconvert ! \
    videoscale ! \
    video/x-raw,width=640,height=480,framerate=30/1 ! \
    x264enc tune=zerolatency bitrate=500 ! \
    rtph264pay ! \
    tcpserversink host=0.0.0.0 port=${PORT}

# Option 2: Try without specifying format
# gst-launch-1.0 -v \
#     v4l2src device=${CAMERA_DEVICE} ! \
#     videoconvert ! \
#     x264enc tune=zerolatency ! \
#     rtph264pay ! \
#     tcpserversink host=0.0.0.0 port=${PORT}

# Option 3: With NVIDIA acceleration (if available)
# gst-launch-1.0 -v \
#     v4l2src device=${CAMERA_DEVICE} ! \
#     videoconvert ! \
#     videoscale ! \
#     video/x-raw,width=1920,height=1080 ! \
#     nvvidconv ! \
#     "video/x-raw(memory:NVMM),format=NV12" ! \
#     nvv4l2h264enc preset-level=1 ! \
#     h264parse ! \
#     rtph264pay name=pay0 pt=96 ! \
#     tcpserversink host=0.0.0.0 port=${PORT}