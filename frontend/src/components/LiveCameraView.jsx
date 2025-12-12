import React, { useState, useEffect, useRef } from 'react'

const LiveCameraView = ({ camera, api, onDetectionUpdate }) => {
  const [detections, setDetections] = useState([])
  const [streamInfo, setStreamInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState(null)
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const wsRef = useRef(null)
  const frameQueueRef = useRef([])
  const isProcessingRef = useRef(false)

  // Fetch camera stream information
  useEffect(() => {
    if (!camera) return

    const fetchStreamInfo = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await api.get(`/api/cameras/${camera.id}/stream`)
        setStreamInfo(response.data)
      } catch (err) {
        console.error('Error fetching camera stream info:', err)
        setError('Failed to fetch camera stream information')
        setStreamInfo(null)
      } finally {
        setLoading(false)
      }
    }

    fetchStreamInfo()
  }, [camera, api])

  // WebSocket connection for camera stream
  useEffect(() => {
    if (!streamInfo || !streamInfo.websocket_url) return

    const connectWebSocket = () => {
      // Determine backend URL based on current host
      // In development, backend runs on port 8000, frontend on 3000
      // When accessed from LAN, use the same hostname with port 8000
      let backendHost
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        // Local development
        backendHost = `${window.location.hostname}:8000`
      } else {
        // LAN access or production - backend is on same host but port 8000
        backendHost = `${window.location.hostname}:8000`
      }
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${backendHost}${streamInfo.websocket_url}`
      
      console.log(`Connecting to WebSocket: ${wsUrl}`)
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected to camera stream')
        setConnected(true)
        setError(null)
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          console.log('WebSocket message received:', message.type)
          
          switch (message.type) {
            case 'connected':
              console.log('Camera stream connected:', message.message)
              break
              
            case 'stream_info':
              console.log('Stream info:', message)
              break
              
            case 'frame':
              // Add frame to queue for processing
              frameQueueRef.current.push(message)
              processFrameQueue()
              break
              
            case 'error':
              console.error('Camera stream error:', message.message)
              setError(message.message)
              break
              
            case 'pong':
              // Keep-alive response
              break
              
            default:
              console.log('Unknown message type:', message.type)
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err, 'Raw data:', event.data)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error event:', error)
        setError('WebSocket connection error - check console for details')
        setConnected(false)
      }

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        setConnected(false)
        
        // Try to reconnect after 3 seconds
        setTimeout(() => {
          if (streamInfo) {
            console.log('Attempting to reconnect...')
            connectWebSocket()
          }
        }, 3000)
      }

      // Send periodic ping to keep connection alive
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, 30000)

      return () => {
        clearInterval(pingInterval)
        if (ws.readyState === WebSocket.OPEN) {
          ws.close()
        }
      }
    }

    const cleanup = connectWebSocket()

    return () => {
      if (cleanup) cleanup()
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
      }
      wsRef.current = null
      frameQueueRef.current = []
      isProcessingRef.current = false
    }
  }, [streamInfo])

  // Process frame queue to display video
  const processFrameQueue = () => {
    if (isProcessingRef.current || frameQueueRef.current.length === 0) {
      return
    }

    isProcessingRef.current = true
    
    // Process all available frames in the queue
    const processFrames = () => {
      while (frameQueueRef.current.length > 0) {
        const frame = frameQueueRef.current.shift()
        
        // Create image from base64 data
        const img = new Image()
        img.onload = () => {
          // Update video element if it exists
          if (videoRef.current) {
            const video = videoRef.current
            const ctx = video.getContext('2d')
            ctx.clearRect(0, 0, video.width, video.height)
            ctx.drawImage(img, 0, 0, video.width, video.height)
          }
        }
        
        img.src = `data:image/jpeg;base64,${frame.data}`
      }
      
      isProcessingRef.current = false
      
      // Schedule next processing batch
      setTimeout(() => {
        if (frameQueueRef.current.length > 0) {
          processFrameQueue()
        }
      }, 33) // ~30 fps
    }

    // Use requestAnimationFrame for smoother rendering
    requestAnimationFrame(processFrames)
  }

  // Initialize canvas for video display
  useEffect(() => {
    if (!videoRef.current) return

    const canvas = videoRef.current
    canvas.width = 640
    canvas.height = 480
    const ctx = canvas.getContext('2d')
    
    // Draw initial black screen
    ctx.fillStyle = '#000'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = '#fff'
    ctx.font = '16px Arial'
    ctx.textAlign = 'center'
    ctx.fillText('Waiting for camera stream...', canvas.width / 2, canvas.height / 2)
  }, [])

  // Handle detection updates (placeholder for now)
  useEffect(() => {
    if (!camera || !connected) return

    // For now, we'll use a placeholder for detections
    // In a production system, this would connect to recognition WebSocket
    const interval = setInterval(() => {
      setDetections([])
    }, 5000)

    return () => {
      clearInterval(interval)
    }
  }, [camera, connected, onDetectionUpdate])

  // Draw detection rectangles on canvas overlay
  useEffect(() => {
    const videoCanvas = videoRef.current
    const overlayCanvas = canvasRef.current
    if (!videoCanvas || !overlayCanvas || !detections.length) return

    const drawDetections = () => {
      const ctx = overlayCanvas.getContext('2d')
      ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height)
      
      // Scale detection coordinates from frame size to display size
      const displayWidth = videoCanvas.width
      const displayHeight = videoCanvas.height

      detections.forEach(detection => {
        if (detection.type === 'face' && detection.location) {
          const [top, right, bottom, left] = detection.location
          
          // Scale coordinates to match display size (assuming original frame is 320x240)
          const scaleX = displayWidth / 320
          const scaleY = displayHeight / 240
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
          // For QR codes, show a text indicator
          ctx.fillStyle = '#ff0000'
          ctx.font = '14px Arial'
          ctx.fillText(`QR Code: ${detection.data}`, 10, 20)
        }
      })
    }

    // Set canvas dimensions to match video canvas
    overlayCanvas.width = videoCanvas.width
    overlayCanvas.height = videoCanvas.height
    
    // Initial draw
    drawDetections()

    // Redraw when detections update
    const observer = new ResizeObserver(() => {
      drawDetections()
    })
    observer.observe(videoCanvas)

    return () => {
      observer.disconnect()
    }
  }, [detections])

  if (loading) {
    return <div className="loading">Loading camera stream...</div>
  }

  if (error) {
    return (
      <div className="error">
        <p>Error: {error}</p>
        <p>Camera: {camera?.name || 'Unknown'}</p>
      </div>
    )
  }

  if (!streamInfo) {
    return (
      <div className="no-stream">
        <p>No camera stream available</p>
        <p>Select a camera to view the live feed</p>
      </div>
    )
  }

  return (
    <div className="camera-view-container">
      <div className="video-container" style={{ position: 'relative' }}>
        <canvas
          ref={videoRef}
          style={{ 
            width: '100%', 
            maxWidth: '640px', 
            height: 'auto', 
            borderRadius: '8px',
            backgroundColor: '#000'
          }}
        />
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
        <div className="connection-status" style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          padding: '5px 10px',
          borderRadius: '4px',
          backgroundColor: connected ? 'rgba(0, 255, 0, 0.7)' : 'rgba(255, 0, 0, 0.7)',
          color: 'white',
          fontSize: '12px',
          fontWeight: 'bold'
        }}>
          {connected ? 'LIVE' : 'CONNECTING...'}
        </div>
      </div>
      
      {/* Camera Information */}
      <div className="camera-info" style={{ marginTop: '10px' }}>
        <h5>{camera?.name || 'Camera'}</h5>
        <p>Status: {connected ? 'Connected' : 'Disconnected'}</p>
        <p>Stream: WebSocket ({frameQueueRef.current.length} frames in queue)</p>
      </div>
      
      {/* Detection Information */}
      <div className="detection-info" style={{ marginTop: '10px' }}>
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
