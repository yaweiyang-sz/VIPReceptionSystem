import subprocess
import os
import threading
import time
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class StreamConverter:
    def __init__(self):
        self.active_streams: Dict[int, subprocess.Popen] = {}
        self.stream_info: Dict[int, dict] = {}
        self.lock = threading.Lock()
        # Scan for existing FFmpeg processes on startup
        self._scan_existing_processes()
    
    def _scan_existing_processes(self):
        """Scan for existing FFmpeg processes and reconnect to them"""
        try:
            import subprocess as sp
            # Find all FFmpeg processes that are converting RTSP to HLS for our cameras
            result = sp.run(['ps', 'aux'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'ffmpeg' in line and 'rtsp://' in line and 'hls' in line:
                    # Extract camera ID from the command line
                    import re
                    camera_match = re.search(r'camera_(\d+)', line)
                    if camera_match:
                        camera_id = int(camera_match.group(1))
                        pid_match = re.search(r'^\S+\s+(\d+)', line)
                        if pid_match:
                            pid = int(pid_match.group(1))
                            # Try to reconnect to the process
                            try:
                                process = sp.Popen(['echo', 'dummy'], stdout=sp.PIPE, stderr=sp.PIPE)
                                process._pid = pid  # Hack to set the PID
                                
                                # Extract output directory from command line
                                output_dir_match = re.search(r'/tmp/hls/camera_\d+', line)
                                if output_dir_match:
                                    output_dir = output_dir_match.group(0)
                                    
                                    with self.lock:
                                        self.active_streams[camera_id] = process
                                        self.stream_info[camera_id] = {
                                            "rtsp_url": "reconnected",  # We don't know the original URL
                                            "hls_url": f"/api/cameras/{camera_id}/hls/playlist.m3u8",
                                            "output_dir": output_dir
                                        }
                                    logger.info(f"Reconnected to existing FFmpeg process for camera {camera_id} (PID: {pid})")
                            except Exception as e:
                                logger.warning(f"Failed to reconnect to FFmpeg process PID {pid}: {e}")
        except Exception as e:
            logger.warning(f"Failed to scan for existing FFmpeg processes: {e}")
        
    def convert_rtsp_to_hls(self, camera_id: int, rtsp_url: str, output_dir: str = "/tmp/hls") -> str:
        """Convert RTSP stream to HLS format for browser playback"""
        
        # Check if stream is already running for this camera
        with self.lock:
            if camera_id in self.active_streams:
                process = self.active_streams[camera_id]
                if process.poll() is None:  # Process is still running
                    logger.info(f"Stream already running for camera {camera_id}, returning existing HLS URL")
                    return f"/api/cameras/{camera_id}/hls/playlist.m3u8"
                else:
                    # Process has terminated, clean it up
                    logger.info(f"Cleaning up terminated stream for camera {camera_id}")
                    del self.active_streams[camera_id]
                    if camera_id in self.stream_info:
                        del self.stream_info[camera_id]
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # HLS output path
        hls_output = os.path.join(output_dir, f"camera_{camera_id}")
        os.makedirs(hls_output, exist_ok=True)
        
        # HLS playlist file
        playlist_file = os.path.join(hls_output, "playlist.m3u8")
        
        # FFmpeg command to convert RTSP to HLS - ultra low latency for live monitoring
        ffmpeg_cmd = [
            "ffmpeg",
            "-rtsp_transport", "tcp",        # Force TCP transport for RTSP
            "-fflags", "nobuffer",           # Reduce buffering
            "-flags", "low_delay",           # Enable low delay mode
            "-analyzeduration", "100000",    # Minimal analysis duration
            "-probesize", "100000",          # Minimal probe size
            "-i", rtsp_url,
            "-c:v", "libx264",               # Re-encode video to fix timestamp issues
            "-preset", "ultrafast",          # Fastest encoding for real-time
            "-tune", "zerolatency",          # Zero latency tuning
            "-crf", "28",                    # Lower quality for maximum speed
            "-g", "5",                       # Very short GOP for minimal latency
            "-r", "10",                      # Lower frame rate to 10fps for speed
            "-b:v", "500k",                  # Lower bitrate for faster transmission
            "-maxrate", "500k",              # Maximum bitrate
            "-bufsize", "1000k",             # Smaller buffer size
            "-c:a", "aac",                   # Encode audio to AAC
            "-ac", "2",
            "-strict", "experimental",
            "-f", "hls",
            "-hls_time", "0.5",              # 0.5-second segments for ultra low latency
            "-hls_list_size", "2",           # Keep only 2 segments in playlist
            "-hls_flags", "delete_segments+append_list+omit_endlist",  # Delete segments, append, no endlist
            "-hls_segment_filename", os.path.join(hls_output, "segment_%03d.ts"),
            playlist_file
        ]
        
        try:
            # Start FFmpeg process
            logger.info(f"Starting FFmpeg process for camera {camera_id} with command: {' '.join(ffmpeg_cmd)}")
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Check if process started successfully
            time.sleep(1)  # Give it a moment to start
            if process.poll() is not None:
                # Process terminated immediately
                stdout, stderr = process.communicate()
                logger.error(f"FFmpeg process for camera {camera_id} terminated immediately. Exit code: {process.returncode}")
                logger.error(f"FFmpeg stdout: {stdout}")
                logger.error(f"FFmpeg stderr: {stderr}")
                raise Exception(f"FFmpeg process terminated with exit code {process.returncode}")
            
            with self.lock:
                self.active_streams[camera_id] = process
                self.stream_info[camera_id] = {
                    "rtsp_url": rtsp_url,
                    "hls_url": f"/api/cameras/{camera_id}/hls/playlist.m3u8",
                    "output_dir": hls_output
                }
            
            logger.info(f"Successfully started RTSP to HLS conversion for camera {camera_id}")
            
            # Return the HLS URL that can be served by the backend
            return f"/api/cameras/{camera_id}/hls/playlist.m3u8"
            
        except Exception as e:
            logger.error(f"Failed to start RTSP to HLS conversion for camera {camera_id}: {e}")
            raise
    
    def stop_stream(self, camera_id: int):
        """Stop the FFmpeg process for a camera"""
        with self.lock:
            if camera_id in self.active_streams:
                process = self.active_streams[camera_id]
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                del self.active_streams[camera_id]
                del self.stream_info[camera_id]
                
                logger.info(f"Stopped RTSP to HLS conversion for camera {camera_id}")
    
    def get_stream_info(self, camera_id: int) -> dict:
        """Get stream information for a camera"""
        with self.lock:
            return self.stream_info.get(camera_id, {})
    
    def cleanup_old_streams(self):
        """Clean up streams that are no longer active"""
        with self.lock:
            cameras_to_remove = []
            for camera_id, process in self.active_streams.items():
                if process.poll() is not None:  # Process has terminated
                    cameras_to_remove.append(camera_id)
            
            for camera_id in cameras_to_remove:
                del self.active_streams[camera_id]
                if camera_id in self.stream_info:
                    del self.stream_info[camera_id]
                logger.info(f"Cleaned up terminated stream for camera {camera_id}")

# Global stream converter instance
stream_converter = StreamConverter()
