import React, { useState, useEffect } from 'react'

const CameraManager = ({ api, onCamerasUpdate }) => {
  const [cameras, setCameras] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [editingCamera, setEditingCamera] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    source: '',
    location: '',
    resolution: '1920x1080',
    fps: 30,
    is_active: true
  })

  // Fetch all cameras
  const fetchCameras = async () => {
    try {
      setLoading(true)
      const response = await api.get('/api/cameras/')
      setCameras(response.data)
    } catch (err) {
      setError('Failed to fetch cameras')
      console.error('Error fetching cameras:', err)
    } finally {
      setLoading(false)
    }
  }

  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  // Submit form (create or update camera)
  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      setLoading(true)
      
      if (editingCamera) {
        // Update existing camera
        await api.put(`/api/cameras/${editingCamera.id}`, formData)
      } else {
        // Create new camera
        await api.post('/api/cameras/', formData)
      }
      
      // Reset form and refresh list
      setShowForm(false)
      setEditingCamera(null)
      setFormData({
        name: '',
        source: '',
        location: '',
        resolution: '1920x1080',
        fps: 30,
        is_active: true
      })
      fetchCameras()
      if (onCamerasUpdate) {
        onCamerasUpdate()
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save camera')
    } finally {
      setLoading(false)
    }
  }

  // Edit camera
  const handleEdit = (camera) => {
    setEditingCamera(camera)
    setFormData({
      name: camera.name,
      source: camera.source,
      location: camera.location,
      resolution: camera.resolution,
      fps: camera.fps,
      is_active: camera.is_active
    })
    setShowForm(true)
  }

  // Delete camera
  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this camera?')) {
      try {
        await api.delete(`/api/cameras/${id}`)
        fetchCameras()
        if (onCamerasUpdate) {
          onCamerasUpdate()
        }
      } catch (err) {
        setError('Failed to delete camera')
      }
    }
  }

  // Toggle camera active status
  const handleToggleActive = async (camera) => {
    try {
      await api.put(`/api/cameras/${camera.id}`, {
        ...camera,
        is_active: !camera.is_active
      })
      fetchCameras()
      if (onCamerasUpdate) {
        onCamerasUpdate()
      }
    } catch (err) {
      setError('Failed to update camera status')
    }
  }

  // Cancel form
  const handleCancel = () => {
    setShowForm(false)
    setEditingCamera(null)
    setFormData({
      name: '',
      source: '',
      location: '',
      resolution: '1920x1080',
      fps: 30,
      is_active: true
    })
  }

  // Get source type for display
  const getSourceType = (source) => {
    if (source.startsWith('rtsp://')) return 'RTSP'
    if (source.startsWith('http://') || source.startsWith('https://')) return 'HTTP'
    if (/^\d+$/.test(source)) return 'Webcam'
    return 'Other'
  }

  useEffect(() => {
    fetchCameras()
  }, [])

  return (
    <div className="camera-manager">
      <div className="section-header">
        <h2>Camera Settings</h2>
        <button 
          className="btn btn-primary"
          onClick={() => setShowForm(true)}
        >
          Add New Camera
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
          <button onClick={() => setError(null)} className="close-btn">×</button>
        </div>
      )}

      {/* Camera Form */}
      {showForm && (
        <div className="form-overlay">
          <div className="form-container">
            <h3>{editingCamera ? 'Edit Camera' : 'Add New Camera'}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Camera Name *</label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="e.g., Main Entrance Camera"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Source *</label>
                  <input
                    type="text"
                    name="source"
                    value={formData.source}
                    onChange={handleInputChange}
                    placeholder="e.g., 0 (webcam), rtsp://url, http://url"
                    required
                  />
                  <small className="help-text">
                    For webcams: use device number (0, 1, 2...)<br />
                    For RTSP: use rtsp://username:password@ip:port/path<br />
                    For HTTP: use http://url/video
                  </small>
                </div>
                <div className="form-group">
                  <label>Location</label>
                  <input
                    type="text"
                    name="location"
                    value={formData.location}
                    onChange={handleInputChange}
                    placeholder="e.g., Main Entrance, VIP Lounge"
                  />
                </div>
                <div className="form-group">
                  <label>Resolution</label>
                  <select
                    name="resolution"
                    value={formData.resolution}
                    onChange={handleInputChange}
                  >
                    <option value="640x480">640x480 (VGA)</option>
                    <option value="1280x720">1280x720 (HD)</option>
                    <option value="1920x1080">1920x1080 (Full HD)</option>
                    <option value="2560x1440">2560x1440 (2K)</option>
                    <option value="3840x2160">3840x2160 (4K)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>FPS (Frames Per Second)</label>
                  <input
                    type="number"
                    name="fps"
                    value={formData.fps}
                    onChange={handleInputChange}
                    min="1"
                    max="60"
                  />
                </div>
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      name="is_active"
                      checked={formData.is_active}
                      onChange={handleInputChange}
                    />
                    Active Camera
                  </label>
                </div>
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={handleCancel}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? 'Saving...' : (editingCamera ? 'Update' : 'Create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Cameras List */}
      <div className="cameras-list">
        {loading && !showForm ? (
          <div className="loading">Loading cameras...</div>
        ) : (
          <div className="cameras-grid">
            {cameras.map(camera => (
              <div key={camera.id} className="camera-card">
                <div className="camera-header">
                  <h4>{camera.name}</h4>
                  <div className="camera-status">
                    <span className={`status-indicator ${camera.is_active ? 'active' : 'inactive'}`}>
                      {camera.is_active ? '● Active' : '○ Inactive'}
                    </span>
                  </div>
                </div>
                
                <div className="camera-details">
                  <div className="detail-row">
                    <strong>Location:</strong> {camera.location || 'Not specified'}
                  </div>
                  <div className="detail-row">
                    <strong>Source:</strong> 
                    <span className="source-type">{getSourceType(camera.source)}</span>
                    <code className="source-url">{camera.source}</code>
                  </div>
                  <div className="detail-row">
                    <strong>Resolution:</strong> {camera.resolution}
                  </div>
                  <div className="detail-row">
                    <strong>FPS:</strong> {camera.fps}
                  </div>
                  <div className="detail-row">
                    <strong>Created:</strong> {new Date(camera.created_at).toLocaleDateString()}
                  </div>
                </div>

                <div className="camera-actions">
                  <button 
                    className={`btn btn-sm ${camera.is_active ? 'btn-warning' : 'btn-success'}`}
                    onClick={() => handleToggleActive(camera)}
                  >
                    {camera.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                  <button 
                    className="btn btn-sm btn-secondary"
                    onClick={() => handleEdit(camera)}
                  >
                    Edit
                  </button>
                  <button 
                    className="btn btn-sm btn-danger"
                    onClick={() => handleDelete(camera.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
            {cameras.length === 0 && (
              <div className="empty-state">
                No cameras configured. Click "Add New Camera" to get started.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default CameraManager
