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
    if (!streamInfo || !streamInfo.websocket_url || !camera) return

    let isMounted = true
    let pingInterval = null
    let reconnectTimeout = null

    const connectWebSocket = () => {
      // Clean up any existing connection
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
      }
      
      // Determine backend URL based on current host
      let backendHost
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        backendHost = `${window.location.hostname}:8000`
      } else {
        backendHost = `${window.location.hostname}:8000`
      }
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${backendHost}${streamInfo.websocket_url}`
      
      console.log(`Connecting to WebSocket for camera ${camera.id}: ${wsUrl}`)
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        if (!isMounted) return
        console.log(`WebSocket connected to camera ${camera.id} stream`)
        setConnected(true)
        setError(null)
      }

      ws.onmessage = (event) => {
        if (!isMounted || !camera) return
        
        try {
          const message = JSON.parse(event.data)
          
          switch (message.type) {
            case 'connected':
              console.log(`Camera ${camera.id} stream connected:`, message.message)
              break
              
            case 'stream_info':
              console.log(`Camera ${camera.id} stream info:`, message)
              break
              
            case 'frame':
              // Strict filtering by camera_id with null checks
              if (camera && message.camera_id !== undefined && message.camera_id === camera.id) {
                // Limit queue size to prevent memory buildup
                if (frameQueueRef.current.length < 5) {
                  frameQueueRef.current.push(message)
                } else {
                  // Drop oldest frame if queue is full
                  frameQueueRef.current.shift()
                  frameQueueRef.current.push(message)
                }
                processFrameQueue()
              } else {
                console.log(`Camera ${camera?.id || 'unknown'}: Ignoring frame from camera ${message.camera_id} (expected ${camera?.id})`)
              }
              break
              
            case 'error':
              console.error(`Camera ${camera.id} stream error:`, message.message)
              setError(message.message)
              break
              
            case 'pong':
              // Keep-alive response
              break
              
            default:
              console.log(`Camera ${camera.id}: Unknown message type:`, message.type)
          }
        } catch (err) {
          console.error(`Camera ${camera.id}: Error parsing WebSocket message:`, err, 'Raw data:', event.data)
        }
      }

      ws.onerror = (error) => {
        if (!isMounted) return
        console.error(`Camera ${camera.id} WebSocket error event:`, error)
        setError('WebSocket connection error')
        setConnected(false)
      }

      ws.onclose = (event) => {
        if (!isMounted) return
        console.log(`Camera ${camera.id} WebSocket disconnected:`, event.code, event.reason)
        setConnected(false)
        
        // Try to reconnect after 3 seconds if still mounted
        if (isMounted && streamInfo) {
          reconnectTimeout = setTimeout(() => {
            console.log(`Camera ${camera.id}: Attempting to reconnect...`)
            connectWebSocket()
          }, 3000)
        }
      }

      // Send periodic ping to keep connection alive
      pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, 30000)
    }

    connectWebSocket()

    return () => {
      isMounted = false
      
      // Clear intervals and timeouts
      if (pingInterval) clearInterval(pingInterval)
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      
      // Close WebSocket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
      }
      wsRef.current = null
      
      // Clear frame queue
      frameQueueRef.current = []
      isProcessingRef.current = false
    }
  }, [streamInfo, camera])  // Depend on camera.id to reconnect when camera changes

  // Process frame queue to display video
  const processFrameQueue = () => {
    if (isProcessingRef.current || frameQueueRef.current.length === 0) {
      return
    }

    isProcessingRef.current = true
    
    // Get the latest frame (drop old frames to maintain real-time)
    let latestFrame = null
    while (frameQueueRef.current.length > 0) {
      latestFrame = frameQueueRef.current.shift()
    }
    
    // Process the latest frame
    if (latestFrame) {
      const img = new Image()
      
      // Use frame dimensions if available, otherwise use default
      const frameWidth = latestFrame.width || 320
      const frameHeight = latestFrame.height || 240
      
      // Update canvas dimensions to match frame aspect ratio
      if (videoRef.current) {
        const canvas = videoRef.current
        const displayWidth = 640  // Fixed display width
        const displayHeight = Math.round(displayWidth * (frameHeight / frameWidth))
        
        // Only resize if dimensions changed significantly
        if (Math.abs(canvas.width - displayWidth) > 10 || Math.abs(canvas.height - displayHeight) > 10) {
          canvas.width = displayWidth
          canvas.height = displayHeight
        }
      }
      
      // Store current processing state to prevent race conditions
      const processingId = Date.now()
      const currentProcessingRef = { id: processingId }
      
      img.onload = () => {
        // Check if this is still the current processing request
        if (currentProcessingRef.id !== processingId) {
          console.log('Skipping stale frame load')
          return
        }
        
        // Update video element if it exists
        if (videoRef.current) {
          const canvas = videoRef.current
          const ctx = canvas.getContext('2d')
          
          // Clear canvas completely
          ctx.clearRect(0, 0, canvas.width, canvas.height)
          
          // Draw image centered and scaled to fit canvas
          const scale = Math.min(canvas.width / img.width, canvas.height / img.height)
          const x = (canvas.width - img.width * scale) / 2
          const y = (canvas.height - img.height * scale) / 2
          
          // Use image smoothing for better quality
          ctx.imageSmoothingEnabled = true
          ctx.imageSmoothingQuality = 'high'
          
          ctx.drawImage(img, x, y, img.width * scale, img.height * scale)
        }
        
        // Mark processing as complete
        isProcessingRef.current = false
        
        // Use requestAnimationFrame for next processing to ensure smooth timing
        requestAnimationFrame(() => {
          if (frameQueueRef.current.length > 0) {
            processFrameQueue()
          }
        })
      }
      
      img.onerror = () => {
        // Check if this is still the current processing request
        if (currentProcessingRef.id !== processingId) {
          return
        }
        
        console.error('Failed to load frame image')
        isProcessingRef.current = false
        
        // Use requestAnimationFrame for next processing
        requestAnimationFrame(() => {
          if (frameQueueRef.current.length > 0) {
            processFrameQueue()
          }
        })
      }
      
      img.src = `data:image/jpeg;base64,${latestFrame.data}`
      
      // Set a timeout to ensure processing doesn't get stuck
      setTimeout(() => {
        if (currentProcessingRef.id === processingId && isProcessingRef.current) {
          console.log('Frame loading timeout, resetting processing state')
          isProcessingRef.current = false
          
          requestAnimationFrame(() => {
            if (frameQueueRef.current.length > 0) {
              processFrameQueue()
            }
          })
        }
      }, 1000) // 1 second timeout
    } else {
      isProcessingRef.current = false
      
      // Use requestAnimationFrame for next processing
      requestAnimationFrame(() => {
        if (frameQueueRef.current.length > 0) {
          processFrameQueue()
        }
      })
    }
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
      
      // Get current frame dimensions from the latest frame in queue
      let frameWidth = 320
      let frameHeight = 240
      if (frameQueueRef.current.length > 0) {
        const latestFrame = frameQueueRef.current[frameQueueRef.current.length - 1]
        frameWidth = latestFrame.width || 320
        frameHeight = latestFrame.height || 240
      }
      
      // Calculate scaling from original frame to displayed canvas
      const displayWidth = videoCanvas.width
      const displayHeight = videoCanvas.height
      
      // Calculate how the image is scaled and positioned on canvas
      const scale = Math.min(displayWidth / frameWidth, displayHeight / frameHeight)
      const xOffset = (displayWidth - frameWidth * scale) / 2
      const yOffset = (displayHeight - frameHeight * scale) / 2

      detections.forEach(detection => {
        if (detection.type === 'face' && detection.location) {
          const [top, right, bottom, left] = detection.location
          
          // Scale coordinates from original frame to display
          const scaledLeft = xOffset + left * scale
          const scaledTop = yOffset + top * scale
          const scaledWidth = (right - left) * scale
          const scaledHeight = (bottom - top) * scale

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
