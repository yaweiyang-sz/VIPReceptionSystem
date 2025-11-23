import React, { useState, useEffect, useRef } from 'react'

const LiveCameraView = ({ camera, api, onDetectionUpdate }) => {
  const [detections, setDetections] = useState([])
  const [streamUrl, setStreamUrl] = useState(null)
  const [loading, setLoading] = useState(false)
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

  // Handle WebSocket connection for real-time detections
  useEffect(() => {
    if (!camera || !streamUrl) return

    const ws = new WebSocket(`ws://localhost:8000/api/recognition/ws/stream/${camera.id}`)
    
    ws.onopen = () => {
      console.log("WebSocket connected for real-time detections")
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === "recognition_update") {
        setDetections(data.detections || [])
        if (onDetectionUpdate) {
          onDetectionUpdate(data.detections || [])
        }
      }
    }
    
    ws.onclose = () => {
      console.log("WebSocket disconnected")
    }
    
    ws.onerror = (error) => {
      console.error("WebSocket error:", error)
    }

    return () => {
      ws.close()
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
          controls
          autoPlay
          muted
          playsInline
          style={{ width: '100%', maxWidth: '640px', height: 'auto', borderRadius: '8px' }}
        >
          <source src={streamUrl} type="video/mp4" />
          Your browser does not support the video tag.
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
