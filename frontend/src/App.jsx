import React, { useState, useEffect } from 'react'
import axios from 'axios'
import AttendeeManager from './components/AttendeeManager'
import CameraManager from './components/CameraManager'
import LiveCameraView from './components/LiveCameraView'

// API base URL - use environment variable or default to relative URL
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

// Configure axios base URL
const api = axios.create({
  baseURL: API_BASE_URL
})

function App() {
  const [systemStats, setSystemStats] = useState(null)
  const [recognitionResult, setRecognitionResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [cameras, setCameras] = useState([])
  const [selectedCamera, setSelectedCamera] = useState(null)
  const [activeTab, setActiveTab] = useState('dashboard') // dashboard, attendees, cameras
  const [cameraStreamUrl, setCameraStreamUrl] = useState(null)
  const [streamLoading, setStreamLoading] = useState(false)
  const [recognitionActive, setRecognitionActive] = useState(false)
  const [annotatedFrame, setAnnotatedFrame] = useState(null)
  const [detections, setDetections] = useState([])
  const [websocket, setWebsocket] = useState(null)

  // Fetch system statistics
  const fetchSystemStats = async () => {
    try {
      const response = await api.get('/api/admin/dashboard/stats')
      setSystemStats(response.data)
    } catch (err) {
      console.error('Error fetching system stats:', err)
    }
  }

  // Fetch cameras
  const fetchCameras = async () => {
    try {
      const response = await api.get('/api/cameras/')
      setCameras(response.data)
      if (response.data.length > 0 && !selectedCamera) {
        setSelectedCamera(response.data[0].id)
      }
    } catch (err) {
      console.error('Error fetching cameras:', err)
    }
  }

  // Fetch camera stream URL
  const fetchCameraStream = async (cameraId) => {
    if (!cameraId) return
    
    try {
      setStreamLoading(true)
      const response = await api.get(`/api/cameras/${cameraId}/stream`)
      setCameraStreamUrl(response.data.stream_url)
    } catch (err) {
      console.error('Error fetching camera stream:', err)
      setCameraStreamUrl(null)
    } finally {
      setStreamLoading(false)
    }
  }

  // Handle camera selection change
  const handleCameraChange = (cameraId) => {
    setSelectedCamera(cameraId)
    fetchCameraStream(cameraId)
  }

  // Start real-time recognition
  const startRealTimeRecognition = async () => {
    if (!selectedCamera) {
      setError("Please select a camera first")
      return
    }

    try {
      setLoading(true)
      setError(null)
      
      // Note: Real-time face recognition via WebSocket is not implemented
      // This would require additional backend infrastructure for real-time processing
      setError("Real-time face recognition is not available in this version. Use HLS video streaming instead.")
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start real-time recognition')
    } finally {
      setLoading(false)
    }
  }

  // Stop real-time recognition
  const stopRealTimeRecognition = async () => {
    try {
      if (websocket) {
        websocket.close()
        setWebsocket(null)
      }
      
      if (selectedCamera) {
        await api.post(`/api/recognition/stop-stream/${selectedCamera}`)
      }
      
      setRecognitionActive(false)
      setAnnotatedFrame(null)
      setDetections([])
      setRecognitionResult(null)
      
    } catch (err) {
      console.error("Error stopping recognition:", err)
    }
  }

  // Simulate face recognition
  const simulateFaceRecognition = async () => {
    setLoading(true)
    setError(null)
    setRecognitionResult(null)
    
    try {
      // This would normally capture an image from the camera
      // For now, we'll simulate with a test image
      const response = await api.post('/api/recognition/auto', {
        image_data: 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k=', // Placeholder base64
        camera_id: selectedCamera || 1
      })
      
      setRecognitionResult(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Recognition failed')
    } finally {
      setLoading(false)
    }
  }

  // Simulate QR code recognition
  const simulateQRRecognition = async () => {
    setLoading(true)
    setError(null)
    setRecognitionResult(null)
    
    try {
      const response = await api.post('/api/recognition/qr', {
        image_data: 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k=', // Placeholder base64
        camera_id: selectedCamera || 1
      })
      
      setRecognitionResult(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'QR recognition failed')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSystemStats()
    fetchCameras()
    
    // Refresh stats every 30 seconds
    const interval = setInterval(fetchSystemStats, 30000)
    return () => clearInterval(interval)
  }, [])

  const renderContent = () => {
    switch (activeTab) {
      case 'attendees':
        return <AttendeeManager api={api} />
      case 'cameras':
        return <CameraManager api={api} onCamerasUpdate={fetchCameras} />
      case 'dashboard':
      default:
        return (
          <div className="main-content">
            {/* System Statistics */}
            {systemStats && (
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-number">{systemStats.total_attendees}</div>
                  <div className="stat-label">Total Attendees</div>
                </div>
                <div className="stat-card">
                  <div className="stat-number">{systemStats.vip_attendees}</div>
                  <div className="stat-label">VIP Attendees</div>
                </div>
                <div className="stat-card">
                  <div className="stat-number">{systemStats.checked_in_attendees}</div>
                  <div className="stat-label">Checked In</div>
                </div>
                <div className="stat-card">
                  <div className="stat-number">{systemStats.today_visits}</div>
                  <div className="stat-label">Today's Visits</div>
                </div>
                <div className="stat-card">
                  <div className="stat-number">{systemStats.active_cameras}</div>
                  <div className="stat-label">Active Cameras</div>
                </div>
              </div>
            )}

            {/* Recognition Section */}
            <div className="recognition-section">
              <h3>Visitor Recognition</h3>
              
              {/* Camera Selection */}
              <div style={{ marginBottom: '1rem' }}>
                <label htmlFor="camera-select" style={{ marginRight: '1rem' }}>Select Camera: </label>
                <select 
                  id="camera-select"
                  value={selectedCamera || ''}
                  onChange={(e) => handleCameraChange(parseInt(e.target.value))}
                  style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ddd' }}
                >
                  {cameras.map(camera => (
                    <option key={camera.id} value={camera.id}>
                      {camera.name} - {camera.location}
                    </option>
                  ))}
                </select>
              </div>

              {/* Live Camera View with Overlay Detection */}
              <div className="camera-feed">
                <LiveCameraView 
                  camera={cameras.find(c => c.id === selectedCamera)}
                  api={api}
                  onDetectionUpdate={(detections) => {
                    setDetections(detections)
                    // Update recognition result if attendee was recognized
                    const faceDetection = detections?.find(d => d.type === "face" && d.attendee_id)
                    if (faceDetection) {
                      setRecognitionResult({
                        success: true,
                        method: "face",
                        confidence: faceDetection.confidence,
                        attendee: { id: faceDetection.attendee_id }
                      })
                    }
                  }}
                />
              </div>

              {/* Recognition Controls */}
              <div className="controls">
                {!recognitionActive ? (
                  <>
                    <button 
                      className="btn btn-primary" 
                      onClick={startRealTimeRecognition}
                      disabled={loading || !selectedCamera}
                    >
                      {loading ? 'Starting...' : 'Start Real-time Recognition'}
                    </button>
                    <button 
                      className="btn btn-secondary" 
                      onClick={simulateFaceRecognition}
                      disabled={loading}
                    >
                      {loading ? 'Processing...' : 'Test Face Recognition'}
                    </button>
                    <button 
                      className="btn btn-secondary" 
                      onClick={simulateQRRecognition}
                      disabled={loading}
                    >
                      {loading ? 'Processing...' : 'Test QR Code Scan'}
                    </button>
                  </>
                ) : (
                  <button 
                    className="btn btn-danger" 
                    onClick={stopRealTimeRecognition}
                  >
                    Stop Real-time Recognition
                  </button>
                )}
              </div>

              {/* Error Display */}
              {error && (
                <div className="recognition-result error">
                  <strong>Error:</strong> {error}
                </div>
              )}

              {/* Recognition Result */}
              {recognitionResult && (
                <div className={`recognition-result ${recognitionResult.success ? '' : 'error'}`}>
                  {recognitionResult.success ? (
                    <div className="attendee-info">
                      <div className="attendee-avatar">
                        {(recognitionResult.attendee?.first_name?.[0] || 'U')}{(recognitionResult.attendee?.last_name?.[0] || 'K')}
                      </div>
                      <div className="attendee-details">
                        <h4>
                          {recognitionResult.attendee?.first_name || 'Unknown'} {recognitionResult.attendee?.last_name || 'User'}
                          {recognitionResult.attendee?.is_vip && <span className="vip-badge">VIP</span>}
                        </h4>
                        <p><strong>Company:</strong> {recognitionResult.attendee?.company || 'Unknown'}</p>
                        <p><strong>Position:</strong> {recognitionResult.attendee?.position || 'Unknown'}</p>
                        <p><strong>Method:</strong> {recognitionResult.method} ({Math.round((recognitionResult.confidence || 0) * 100)}% confidence)</p>
                      </div>
                    </div>
                  ) : (
                    <p>{recognitionResult.message || 'Recognition failed'}</p>
                  )}
                </div>
              )}
            </div>

            {/* System Information */}
            <div className="dashboard">
              <div className="card">
                <h3>System Status</h3>
                <p>Backend: <span style={{ color: '#28a745' }}>Connected</span></p>
                <p>Database: <span style={{ color: '#28a745' }}>Healthy</span></p>
                <p>Cameras: <span style={{ color: '#28a745' }}>{cameras.length} Active</span></p>
              </div>

              <div className="card">
                <h3>Quick Actions</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <button 
                    className="btn btn-secondary" 
                    onClick={() => setActiveTab('attendees')}
                  >
                    Manage Attendees
                  </button>
                  <button 
                    className="btn btn-secondary" 
                    onClick={() => setActiveTab('cameras')}
                  >
                    Camera Settings
                  </button>
                </div>
              </div>

              <div className="card">
                <h3>Recent Activity</h3>
                <p>System running normally</p>
                <p>All services operational</p>
                <p>Ready for visitor recognition</p>
              </div>
            </div>
          </div>
        )
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>VIP Reception System</h1>
        <p>Aviation Interior Exhibition - Visitor Recognition</p>
        
        {/* Navigation Tabs */}
        <nav className="nav-tabs">
          <button 
            className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            Dashboard
          </button>
          <button 
            className={`nav-tab ${activeTab === 'attendees' ? 'active' : ''}`}
            onClick={() => setActiveTab('attendees')}
          >
            Manage Attendees
          </button>
          <button 
            className={`nav-tab ${activeTab === 'cameras' ? 'active' : ''}`}
            onClick={() => setActiveTab('cameras')}
          >
            Camera Settings
          </button>
        </nav>
      </header>

      {renderContent()}
    </div>
  )
}

export default App
