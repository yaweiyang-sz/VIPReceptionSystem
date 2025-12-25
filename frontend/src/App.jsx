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
  const [activeTab, setActiveTab] = useState('dashboard')
  const [recognitionActive, setRecognitionActive] = useState(false)
  const [detections, setDetections] = useState([])

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

  // Handle camera selection change
  const handleCameraChange = (cameraId) => {
    setSelectedCamera(cameraId)
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
      setRecognitionActive(true)
      // Note: Real-time recognition would be handled via WebSocket in LiveCameraView
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start real-time recognition')
    } finally {
      setLoading(false)
    }
  }

  // Stop real-time recognition
  const stopRealTimeRecognition = async () => {
    setRecognitionActive(false)
    setRecognitionResult(null)
  }

  // Simulate face recognition
  const simulateFaceRecognition = async () => {
    setLoading(true)
    setError(null)
    setRecognitionResult(null)
    
    try {
      const response = await api.post('/api/recognition/auto', {
        image_data: 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k=',
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
        image_data: 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k=',
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
          <div style={{ padding: '20px', width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Visitor Recognition Section - Full width */}
            <div style={{ width: '100%' }}>
              
              {/* Live Camera View - Takes full width */}
              <div style={{ width: '100%', marginBottom: '15px' }}>
                <LiveCameraView 
                  camera={cameras.find(c => c.id === selectedCamera)}
                  api={api}
                  onDetectionUpdate={(detections) => {
                    setDetections(detections)
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

              {/* Camera Selection - Below LiveCameraView */}
              <div style={{ marginBottom: '15px' }}>
                <label style={{ marginRight: '10px', fontWeight: 'bold' }}>Select Camera:</label>
                <select 
                  value={selectedCamera || ''}
                  onChange={(e) => handleCameraChange(parseInt(e.target.value))}
                  style={{ padding: '8px', width: '300px', borderRadius: '4px', border: '1px solid #ccc' }}
                >
                  {cameras.map(camera => (
                    <option key={camera.id} value={camera.id}>
                      {camera.name} - {camera.location}
                    </option>
                  ))}
                </select>
              </div>

              {/* Error Display */}
              {error && (
                <div style={{ padding: '10px', background: '#f8d7da', color: '#721c24', borderRadius: '4px', marginBottom: '15px' }}>
                  <strong>Error:</strong> {error}
                </div>
              )}

              {/* Simple Recognition Result */}
              {recognitionResult && (
                <div style={{ 
                  padding: '15px', 
                  background: recognitionResult.success ? '#d4edda' : '#f8d7da',
                  color: recognitionResult.success ? '#155724' : '#721c24',
                  borderRadius: '4px'
                }}>
                  {recognitionResult.success ? (
                    <div>
                      <strong>Recognized:</strong> Attendee #{recognitionResult.attendee?.id} 
                      ({Math.round((recognitionResult.confidence || 0) * 100)}% confidence)
                    </div>
                  ) : (
                    <div>{recognitionResult.message || 'Recognition failed'}</div>
                  )}
                </div>
              )}
            </div>
          </div>
        )
    }
  }

  return (
    <div>
      <header style={{ background: '#343a40', color: 'white', padding: '15px 20px', position: 'relative' }}>
        {/* Left side: Title and subtitle */}
        <div style={{ marginBottom: '15px' }}>
          <h1 style={{ margin: 0 }}>VIP Reception System</h1>
          <p style={{ margin: '5px 0 0 0', opacity: 0.8 }}>Aviation Interior Exhibition - Visitor Recognition</p>
        </div>
        
        {/* Main header row: Navigation on left, Stats on right */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
          {/* Simple Navigation - Left side */}
          <div style={{ display: 'flex', gap: '10px' }}>
            <button 
              onClick={() => setActiveTab('dashboard')}
              style={{ 
                padding: '8px 15px', 
                background: activeTab === 'dashboard' ? '#007bff' : 'transparent',
                color: activeTab === 'dashboard' ? 'white' : '#ccc',
                border: '1px solid #ccc',
                borderRadius: '4px'
              }}
            >
              Dashboard
            </button>
            <button 
              onClick={() => setActiveTab('attendees')}
              style={{ 
                padding: '8px 15px', 
                background: activeTab === 'attendees' ? '#007bff' : 'transparent',
                color: activeTab === 'attendees' ? 'white' : '#ccc',
                border: '1px solid #ccc',
                borderRadius: '4px'
              }}
            >
              Manage Attendees
            </button>
            <button 
              onClick={() => setActiveTab('cameras')}
              style={{ 
                padding: '8px 15px', 
                background: activeTab === 'cameras' ? '#007bff' : 'transparent',
                color: activeTab === 'cameras' ? 'white' : '#ccc',
                border: '1px solid #ccc',
                borderRadius: '4px'
              }}
            >
              Camera Settings
            </button>
          </div>
          
          {/* System Statistics - Right side, aligned with navigation bottom */}
          {systemStats && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
              <div style={{ textAlign: 'center', minWidth: '70px' }}>
                <div style={{ fontSize: '18px', fontWeight: 'bold' }}>{systemStats.total_attendees}</div>
                <div style={{ fontSize: '10px', opacity: 0.8 }}>Total</div>
              </div>
              <div style={{ textAlign: 'center', minWidth: '70px' }}>
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#ff9900' }}>{systemStats.vip_attendees}</div>
                <div style={{ fontSize: '10px', opacity: 0.8 }}>VIP</div>
              </div>
              <div style={{ textAlign: 'center', minWidth: '70px' }}>
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#28a745' }}>{systemStats.checked_in_attendees}</div>
                <div style={{ fontSize: '10px', opacity: 0.8 }}>Checked In</div>
              </div>
              <div style={{ textAlign: 'center', minWidth: '70px' }}>
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#17a2b8' }}>{systemStats.today_visits}</div>
                <div style={{ fontSize: '10px', opacity: 0.8 }}>Today</div>
              </div>
              <div style={{ textAlign: 'center', minWidth: '70px' }}>
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#6f42c1' }}>{systemStats.active_cameras}</div>
                <div style={{ fontSize: '10px', opacity: 0.8 }}>Cameras</div>
              </div>
            </div>
          )}
        </div>
      </header>

      {renderContent()}
    </div>
  )
}

export default App
