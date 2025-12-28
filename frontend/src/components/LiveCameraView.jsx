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
              
            case 'recognition_update':
              // Process recognition updates directly since we're receiving them
              console.log(`Camera ${camera.id}: Processing recognition update:`, message)
              if (message.camera_id === camera.id) {
                console.log('Processing recognition update for camera:', camera.id, 'Detections:', message.detections)
                const updatedDetections = message.detections || []
                
                // Enhance face detections with VIP information
                const enhancedDetections = updatedDetections.map(detection => {
                  console.log('Processing detection:', detection)
                  if (detection.type === 'face' && detection.attendee_id) {
                    const isVip = detection.is_vip !== undefined ? detection.is_vip : (detection.attendee_id % 3 === 0)
                    
                    return {
                      ...detection,
                      is_vip: isVip,
                      vip_info: isVip ? {
                        priority: 'High',
                        welcome_message: `Welcome ${detection.attendee_name || 'VIP Guest'}!`,
                        special_requirements: 'Private lounge access'
                      } : null
                    }
                  }
                  return detection
                })
                
                console.log('Enhanced detections:', enhancedDetections)
                setDetections(enhancedDetections)
                
                if (onDetectionUpdate) {
                  onDetectionUpdate(enhancedDetections)
                }
              }
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

  // Handle WebSocket connection for recognition updates
  useEffect(() => {
    if (!camera || !connected) return

    let isMounted = true
    let recognitionWs = null
    let reconnectTimeout = null

    const connectRecognitionWebSocket = () => {
      // Determine backend URL based on current host (same logic as camera stream WebSocket)
      let backendHost
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        backendHost = `${window.location.hostname}:8000`
      } else {
        backendHost = `${window.location.hostname}:8000`
      }
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${backendHost}/api/ws/recognition`
      
      console.log(`Connecting to recognition WebSocket: ${wsUrl}`)
      recognitionWs = new WebSocket(wsUrl)

      recognitionWs.onopen = () => {
        if (!isMounted) return
        console.log('Recognition WebSocket connected')
        
        // Subscribe to camera recognition updates
        if (camera) {
          recognitionWs.send(JSON.stringify({
            type: 'subscribe',
            camera_id: camera.id
          }))
        }
      }

      recognitionWs.onmessage = (event) => {
        if (!isMounted || !camera) return
        
        try {
          const message = JSON.parse(event.data)
          // console.log('Recognition WebSocket message received:', message)
          
          if (message.type === 'recognition_update' && message.camera_id === camera.id) {
            // console.log('Processing recognition update for camera:', camera.id, 'Detections:', message.detections)
            // Update detections with VIP information
            const updatedDetections = message.detections || []
            
            // Enhance face detections with VIP information
            const enhancedDetections = updatedDetections.map(detection => {
              // console.log('Processing detection:', detection)
              if (detection.type === 'face' && detection.attendee_id) {
                // Use is_vip from backend if available, otherwise use example logic
                const isVip = detection.is_vip !== undefined ? detection.is_vip : (detection.attendee_id % 3 === 0)
                
                return {
                  ...detection,
                  is_vip: isVip,
                  vip_info: isVip ? {
                    priority: 'High',
                    welcome_message: `Welcome ${detection.attendee_name || 'VIP Guest'}!`,
                    special_requirements: 'Private lounge access'
                  } : null
                }
              }
              return detection
            })
            
            // console.log('Enhanced detections:', enhancedDetections)
            setDetections(enhancedDetections)
            
            // Notify parent component if callback provided
            if (onDetectionUpdate) {
              onDetectionUpdate(enhancedDetections)
            }
          }
        } catch (err) {
          console.error('Error parsing recognition message:', err, 'Raw data:', event.data)
        }
      }

      recognitionWs.onerror = (error) => {
        if (!isMounted) return
        console.error('Recognition WebSocket error:', error)
      }

      recognitionWs.onclose = (event) => {
        if (!isMounted) return
        console.log('Recognition WebSocket disconnected:', event.code, event.reason)
        
        // Try to reconnect after 5 seconds
        if (isMounted) {
          reconnectTimeout = setTimeout(() => {
            console.log('Attempting to reconnect recognition WebSocket...')
            connectRecognitionWebSocket()
          }, 5000)
        }
      }
    }

    connectRecognitionWebSocket()

    return () => {
      isMounted = false
      
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      
      if (recognitionWs && recognitionWs.readyState === WebSocket.OPEN) {
        recognitionWs.close()
      }
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

          // Determine color based on VIP status
          const isVip = detection.is_vip || false
          const strokeColor = isVip ? '#ff9900' : '#00ff00'  // Orange for VIP, green for regular
          const fillColor = isVip ? '#ff9900' : '#00ff00'
          
          // Draw face detection rectangle
          ctx.strokeStyle = strokeColor
          ctx.lineWidth = isVip ? 3 : 2  // Thicker border for VIP
          ctx.strokeRect(scaledLeft, scaledTop, scaledWidth, scaledHeight)
          
          // Draw VIP crown icon if VIP
          if (isVip) {
            // Simple crown drawing
            ctx.fillStyle = '#ffcc00'
            ctx.beginPath()
            ctx.moveTo(scaledLeft + scaledWidth / 2, scaledTop - 15)
            ctx.lineTo(scaledLeft + scaledWidth / 2 - 10, scaledTop - 5)
            ctx.lineTo(scaledLeft + scaledWidth / 2 - 5, scaledTop - 5)
            ctx.lineTo(scaledLeft + scaledWidth / 2, scaledTop - 10)
            ctx.lineTo(scaledLeft + scaledWidth / 2 + 5, scaledTop - 5)
            ctx.lineTo(scaledLeft + scaledWidth / 2 + 10, scaledTop - 5)
            ctx.closePath()
            ctx.fill()
          }
          
          // Draw label with attendee name if available
          let labelText = `Face (${Math.round(detection.confidence * 100)}%)`
          if (detection.attendee_name) {
            labelText = `${detection.attendee_name} (${Math.round(detection.confidence * 100)}%)`
          }
          
          if (isVip) {
            labelText = `⭐ ${labelText} ⭐`
          }
          
          ctx.fillStyle = fillColor
          ctx.font = isVip ? 'bold 14px Arial' : '14px Arial'
          ctx.fillText(labelText, scaledLeft, scaledTop - 10)
          
          // Draw additional VIP info if available
          if (isVip && detection.vip_info) {
            ctx.font = '12px Arial'
            ctx.fillText(detection.vip_info.welcome_message || 'VIP Guest', scaledLeft, scaledTop - 30)
          }
        }
        
        if (detection.type === 'qr_code') {
          // For QR codes, show a text indicator
          ctx.fillStyle = '#007bff'
          ctx.font = '14px Arial'
          ctx.fillText('QR Code Detected', xOffset + 10, yOffset + 20)
        }
      })
    }

    // Set overlay canvas dimensions to match video canvas
    overlayCanvas.width = videoCanvas.width
    overlayCanvas.height = videoCanvas.height
    
    drawDetections()
  }, [detections])

  // Simple layout with video on left and detections on right
  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'row', 
      gap: '20px', 
      height: '100%',
      minHeight: '500px'
    }}>
      {/* Video Stream */}
      <div style={{ 
        flex: 1, 
        display: 'flex', 
        flexDirection: 'column',
        minHeight: '500px'
      }}>
        <div style={{ 
          position: 'relative', 
          flex: 1,
          backgroundColor: '#000',
          borderRadius: '8px',
          overflow: 'hidden'
        }}>
          <canvas
            ref={videoRef}
            style={{ 
              width: '100%',
              height: '100%',
              display: 'block'
            }}
          />
          <canvas
            ref={canvasRef}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'none'
            }}
          />
          <div style={{
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
        
        {/* Camera Info */}
        <div style={{ 
          marginTop: '10px', 
          padding: '12px', 
          backgroundColor: '#f8f9fa', 
          borderRadius: '8px'
        }}>
          <h5 style={{ marginBottom: '8px', color: '#333', fontSize: '16px' }}>{camera?.name || 'Camera'}</h5>
          <div style={{ 
            display: 'flex', 
            flexWrap: 'wrap',
            justifyContent: 'space-between', 
            gap: '10px',
            fontSize: '14px' 
          }}>
            <div>
              <strong>Status:</strong> <span style={{ color: connected ? '#28a745' : '#dc3545' }}>
                {connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <div>
              <strong>Frames in queue:</strong> {frameQueueRef.current.length}
            </div>
            <div>
              <strong>Stream:</strong> WebSocket
            </div>
          </div>
        </div>
      </div>
      
      {/* Active Detections */}
      <div style={{ 
        flex: 1, 
        display: 'flex', 
        flexDirection: 'column',
        minHeight: '500px'
      }}>
        <div style={{ 
          flex: 1,
          padding: '15px', 
          backgroundColor: '#f5f5f5', 
          borderRadius: '8px',
          overflowY: 'auto'
        }}>
          <div style={{ 
            marginBottom: '15px', 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center'
          }}>
            <h5 style={{ margin: 0, color: '#333', fontSize: '18px' }}>Active Detections</h5>
            <div style={{ 
              padding: '4px 12px', 
              backgroundColor: detections.length > 0 ? '#4caf50' : '#6c757d',
              color: 'white',
              borderRadius: '20px',
              fontSize: '14px',
              fontWeight: 'bold'
            }}>
              {detections.length} {detections.length === 1 ? 'Detection' : 'Detections'}
            </div>
          </div>
          
          {detections.length > 0 ? (
            <div>
              {detections.map((detection, index) => (
                <div key={index} style={{ 
                  marginBottom: '12px', 
                  padding: '12px', 
                  backgroundColor: detection.is_vip ? '#fff8e1' : '#fff',
                  borderLeft: detection.is_vip ? '4px solid #ff9900' : '4px solid #4caf50',
                  borderRadius: '6px',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <strong style={{ 
                        color: detection.is_vip ? '#ff9900' : '#4caf50',
                        fontSize: '16px'
                      }}>
                        {detection.type.toUpperCase()}
                      </strong>
                      {detection.is_vip && (
                        <span style={{ 
                          padding: '2px 8px', 
                          backgroundColor: '#ff9900',
                          color: 'white',
                          borderRadius: '12px',
                          fontSize: '12px',
                          fontWeight: 'bold'
                        }}>
                          ⭐ VIP
                        </span>
                      )}
                    </div>
                    {detection.confidence && (
                      <span style={{ 
                        padding: '4px 10px', 
                        backgroundColor: detection.confidence > 0.8 ? '#4caf50' : detection.confidence > 0.6 ? '#ff9800' : '#f44336',
                        color: 'white',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: 'bold'
                      }}>
                        {Math.round(detection.confidence * 100)}% confidence
                      </span>
                    )}
                  </div>
                  
                  {detection.type === 'face' && (
                    <div style={{ marginTop: '8px' }}>
                      {detection.attendee_name && (
                        <div style={{ marginBottom: '6px', fontSize: '15px' }}>
                          <strong>Name:</strong> {detection.attendee_name}
                        </div>
                      )}
                      {detection.company && (
                        <div style={{ marginBottom: '4px', fontSize: '14px', color: '#555' }}>
                          <strong>Company:</strong> {detection.company}
                        </div>
                      )}
                      {detection.position && (
                        <div style={{ marginBottom: '4px', fontSize: '14px', color: '#555' }}>
                          <strong>Position:</strong> {detection.position}
                        </div>
                      )}
                      {detection.attendee_id && (
                        <div style={{ marginBottom: '4px', fontSize: '13px', color: '#777' }}>
                          <strong>Attendee ID:</strong> {detection.attendee_id}
                        </div>
                      )}
                      
                      {detection.is_vip && (
                        <div style={{ 
                          marginTop: '10px', 
                          padding: '10px', 
                          backgroundColor: '#fff3cd', 
                          borderRadius: '6px',
                          border: '1px solid #ffeaa7'
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '6px' }}>
                            <strong style={{ color: '#856404', fontSize: '15px' }}>VIP Status</strong>
                            <span style={{ marginLeft: '8px', color: '#856404', fontSize: '14px' }}>
                              ⭐ Priority Access Granted
                            </span>
                          </div>
                          {detection.vip_info && (
                            <div style={{ marginTop: '6px', fontSize: '14px', color: '#856404' }}>
                              <div style={{ marginBottom: '4px' }}>
                                <strong>Welcome:</strong> {detection.vip_info.welcome_message}
                              </div>
                              <div>
                                <strong>Special Requirements:</strong> {detection.vip_info.special_requirements}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  
                  {detection.type === 'qr_code' && (
                    <div style={{ marginTop: '8px' }}>
                      <div style={{ fontSize: '15px' }}>
                        <strong>QR Code Data:</strong>
                      </div>
                      <div style={{ 
                        marginTop: '6px', 
                        padding: '8px', 
                        backgroundColor: '#f8f9fa', 
                        borderRadius: '4px',
                        fontFamily: 'monospace',
                        fontSize: '13px',
                        wordBreak: 'break-all'
                      }}>
                        {detection.data}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              justifyContent: 'center', 
              alignItems: 'center', 
              color: '#666',
              textAlign: 'center',
              height: '100%'
            }}>
              <div style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.5 }}>👁️</div>
              <p style={{ fontSize: '18px', marginBottom: '8px' }}>No objects detected</p>
              <p style={{ fontSize: '14px', color: '#888' }}>Waiting for face recognition...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default LiveCameraView
