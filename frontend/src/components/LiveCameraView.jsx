import React, { useState, useEffect, useRef } from 'react'
import Hls from 'hls.js'

const LiveCameraView = ({ camera, api, onDetectionUpdate }) => {
  const [detections, setDetections] = useState([])
  const [streamUrl, setStreamUrl] = useState(null)
  const [loading, setLoading] = useState(false)
  const [hls, setHls] = useState(null)
  const videoRef = useRef(null)
  const canvasRef = useRef(null)

  // Fetch camera stream URL
  useEffect(() => {
    if (!camera) return

    const fetchStreamUrl = async () => {
      try {
        setLoading(true)
        const response = await api.get(`/api/cameras/${camera.id}/stream`)
        setStreamUrl(response.data.stream_url)
      } catch (err) {
        console.error('Error fetching camera stream:', err)
        setStreamUrl(null)
      } finally {
        setLoading(false)
      }
    }

    fetchStreamUrl()
  }, [camera, api])

  // Initialize HLS.js when stream URL is available
  useEffect(() => {
    if (!streamUrl || !videoRef.current) return

    // Check if HLS.js is available
    if (!Hls.isSupported()) {
      console.error('HLS.js is not supported in this browser.')
      return
    }

    const video = videoRef.current
    const hlsInstance = new Hls({
      enableWorker: false,
      lowLatencyMode: true,
      backBufferLength: 1,           // Reduce buffer for lower latency
      maxBufferLength: 2,            // Smaller buffer
      maxMaxBufferLength: 3,         // Maximum buffer size
      maxBufferSize: 3 * 1000 * 1000, // 3MB buffer
      maxBufferHole: 0.5,            // Reduce buffer hole tolerance
      highBufferWatchdogPeriod: 1,   // Faster buffer monitoring
      nudgeOffset: 0.1,              // Smaller nudge offset
      nudgeMaxRetry: 2,              // Fewer retries
      maxFragLookUpTolerance: 0.1,   // Reduce fragment lookup tolerance
      liveSyncDurationCount: 1,      // Sync to live edge
      liveMaxLatencyDurationCount: 2, // Maximum latency
      liveDurationInfinity: false,   // Don't use infinite duration
      liveBackBufferLength: 0,       // No back buffer for live
      maxLiveSyncPlaybackRate: 1.1   // Allow slight speedup to catch up
    })

    hlsInstance.loadSource(streamUrl)
    hlsInstance.attachMedia(video)

    hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
      console.log('HLS manifest parsed, starting video playback')
      video.play().catch(err => {
        console.error('Failed to play video:', err)
      })
    })

    hlsInstance.on(Hls.Events.ERROR, (event, data) => {
      console.error('HLS error:', data)
      if (data.fatal) {
        switch (data.type) {
          case Hls.ErrorTypes.NETWORK_ERROR:
            console.error('HLS network error, trying to recover...')
            hlsInstance.startLoad()
            break
          case Hls.ErrorTypes.MEDIA_ERROR:
            console.error('HLS media error, recovering...')
            hlsInstance.recoverMediaError()
            break
          default:
            console.error('Fatal HLS error, cannot recover')
            hlsInstance.destroy()
            break
        }
      }
    })

    setHls(hlsInstance)

    return () => {
      if (hlsInstance) {
        hlsInstance.destroy()
      }
    }
  }, [streamUrl])

  // Handle video stream and periodic detection updates
  useEffect(() => {
    if (!camera || !streamUrl) return

    // For now, we'll use a placeholder for detections since real-time
    // face recognition via WebSocket is not implemented
    // In a production system, this would connect to a WebSocket or polling endpoint
    const interval = setInterval(() => {
      // Simulate detection updates (remove this in production)
      setDetections([])
    }, 5000)

    return () => {
      clearInterval(interval)
    }
  }, [camera, streamUrl, onDetectionUpdate])

  // Draw detection rectangles on canvas overlay
  useEffect(() => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas || !detections.length) return

    const drawDetections = () => {
      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      
      // Scale detection coordinates from frame size to video display size
      const videoWidth = video.videoWidth
      const videoHeight = video.videoHeight
      const displayWidth = video.offsetWidth
      const displayHeight = video.offsetHeight
      
      const scaleX = displayWidth / videoWidth
      const scaleY = displayHeight / videoHeight

      detections.forEach(detection => {
        if (detection.type === 'face' && detection.location) {
          const [top, right, bottom, left] = detection.location
          
          // Scale coordinates to match video display size
          const scaledLeft = left * scaleX
          const scaledTop = top * scaleY
          const scaledWidth = (right - left) * scaleX
          const scaledHeight = (bottom - top) * scaleY

          // Draw face detection rectangle
          ctx.strokeStyle = '#00ff00'
          ctx.lineWidth = 2
          ctx.strokeRect(scaledLeft, scaledTop, scaledWidth, scaledHeight)
          
          // Draw label
          ctx.fillStyle = '#00ff00'
          ctx.font = '14px Arial'
          ctx.fillText(`Face (${Math.round(detection.confidence * 100)}%)`, scaledLeft, scaledTop - 5)
        }
        
        if (detection.type === 'qr_code') {
          // For QR codes, we don't have location data from pyzbar
          // So we'll just show a text indicator
          ctx.fillStyle = '#ff0000'
          ctx.font = '14px Arial'
          ctx.fillText(`QR Code: ${detection.data}`, 10, 20)
        }
      })
    }

    // Redraw when video dimensions change or detections update
    const observer = new ResizeObserver(drawDetections)
    observer.observe(video)

    // Initial draw
    drawDetections()

    return () => {
      observer.disconnect()
    }
  }, [detections])

  if (loading) {
    return <div className="loading">Loading camera stream...</div>
  }

  if (!streamUrl) {
    return (
      <div className="no-stream">
        <p>No camera stream available</p>
        <p>Select a camera to view the live feed</p>
      </div>
    )
  }

  return (
    <div className="camera-view-container">
      <div className="video-container">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          style={{ width: '100%', maxWidth: '640px', height: 'auto', borderRadius: '8px' }}
        >
          Your browser doesn't support HLS video playback.
        </video>
        <canvas
          ref={canvasRef}
          className="detection-overlay"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none'
          }}
        />
      </div>
      
      {/* Detection Information */}
      <div className="detection-info">
        <h5>Active Detections:</h5>
        {detections.length > 0 ? (
          <ul>
            {detections.map((detection, index) => (
              <li key={index}>
                <strong>{detection.type.toUpperCase()}:</strong> 
                {detection.type === 'face' && detection.attendee_id && (
                  <span> Attendee ID: {detection.attendee_id} ({(detection.confidence * 100).toFixed(1)}% confidence)</span>
                )}
                {detection.type === 'qr_code' && (
                  <span> Data: {detection.data}</span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p>No objects detected</p>
        )}
      </div>
    </div>
  )
}

export default LiveCameraView
