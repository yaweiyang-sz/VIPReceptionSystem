#!/bin/bash

ffmpeg -f v4l2   -input_format mjpeg   -framerate 25   -video_size 1920x1080   -i /dev/video0  -f rtsp   -rtsp_transport tcp   rtsp://localhost:8554/cam