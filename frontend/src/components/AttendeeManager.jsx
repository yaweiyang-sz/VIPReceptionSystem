import React, { useState, useEffect } from 'react'

const AttendeeManager = ({ api }) => {
  const [attendees, setAttendees] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [editingAttendee, setEditingAttendee] = useState(null)
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    company: '',
    position: '',
    phone: '',
    is_vip: false,
    photo_url: '',
    photo_key: Date.now() // Add a key to force image reload
  })

  // Fetch all attendees
  const fetchAttendees = async () => {
    try {
      setLoading(true)
      const response = await api.get('/api/attendees/')
      setAttendees(response.data)
    } catch (err) {
      setError('Failed to fetch attendees')
      console.error('Error fetching attendees:', err)
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

  // Handle file upload for face photo
  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    try {
      setLoading(true)
      
      // First, create the attendee if we're in create mode
      let attendeeId = editingAttendee?.id
      
      if (!attendeeId) {
        // We need to create the attendee first to get an ID
        const createResponse = await api.post('/api/attendees/', {
          first_name: formData.first_name || 'Temp',
          last_name: formData.last_name || 'User',
          email: formData.email || `temp-${Date.now()}@example.com`,
          company: formData.company || '',
          position: formData.position || '',
          phone: formData.phone || '',
          is_vip: formData.is_vip || false
        })
        attendeeId = createResponse.data.id
        setEditingAttendee(createResponse.data)
        
        // Update form data with the new attendee ID
        setFormData(prev => ({
          ...prev,
          ...createResponse.data
        }))
      }

      // Now upload the photo for face encoding
      const formDataObj = new FormData()
      formDataObj.append('file', file)

      const uploadResponse = await api.post(
        `/api/attendees/${attendeeId}/upload-photo`,
        formDataObj,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      )

      // After successful upload, use the backend URL with cache-busting
      const backendUrl = 'http://localhost:8000'
      const timestamp = new Date().getTime()
      const backendPhotoUrl = `${backendUrl}/api/attendees/${attendeeId}/photo?t=${timestamp}`
      
      // Update form data with the backend URL and force image reload
      setFormData(prev => ({
        ...prev,
        photo_url: backendPhotoUrl,
        photo_key: Date.now(), // Force image reload by changing the key
        has_face_encoding: uploadResponse.data.face_encoding_saved
      }))
      
      // Refresh attendees list to sync with database
      await fetchAttendees()
      
      // Show appropriate message based on face detection results
      const faceDetails = uploadResponse.data.face_detection_details
      if (uploadResponse.data.face_encoding_saved) {
        alert(`✅ Face photo uploaded and encoded successfully!\n\n${faceDetails.message}`)
      } else {
        alert(`⚠️ Photo uploaded successfully, but face recognition is not available.\n\n${faceDetails.message}\n\nPlease upload a different photo with a clear, visible face for face recognition to work.`)
      }
      
    } catch (err) {
      console.error('Photo upload error:', err)
      setError(err.response?.data?.detail || 'Failed to upload and process photo')
    } finally {
      setLoading(false)
    }
  }

  // Submit form (create or update attendee)
  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      setLoading(true)
      
      if (editingAttendee) {
        // Update existing attendee
        await api.put(`/api/attendees/${editingAttendee.id}`, formData)
      } else {
        // Create new attendee
        await api.post('/api/attendees/', formData)
      }
      
      // Reset form and refresh list
      setShowForm(false)
      setEditingAttendee(null)
      setFormData({
        first_name: '',
        last_name: '',
        email: '',
        company: '',
        position: '',
        phone: '',
        is_vip: false,
        photo_url: ''
      })
      fetchAttendees()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save attendee')
    } finally {
      setLoading(false)
    }
  }

  // Edit attendee
  const handleEdit = (attendee) => {
    setEditingAttendee(attendee)
    
    // Build the photo URL - ALWAYS use full backend URL for images
    const backendUrl = 'http://localhost:8000' // Hardcoded for debugging
    let photoUrl = ''
    if (attendee.photo_url) {
      // If photo_url is already a full URL, use it directly with cache-busting
      if (attendee.photo_url.startsWith('http')) {
        const timestamp = new Date().getTime()
        photoUrl = `${attendee.photo_url}?t=${timestamp}`
      } else {
        // If it's a relative path, construct the full backend URL with cache-busting
        const timestamp = new Date().getTime()
        photoUrl = `${backendUrl}${attendee.photo_url}?t=${timestamp}`
      }
    } else if (attendee.id) {
      // Construct the photo URL from the API (full backend URL)
      // Add cache-busting timestamp to force browser to reload the image
      const timestamp = new Date().getTime()
      photoUrl = `${backendUrl}/api/attendees/${attendee.id}/photo?t=${timestamp}`
    }
    
    console.log('Photo URL constructed:', photoUrl)
    console.log('Attendee data:', attendee)
    console.log('Backend URL:', backendUrl)
    
    setFormData({
      first_name: attendee.first_name,
      last_name: attendee.last_name,
      email: attendee.email,
      company: attendee.company,
      position: attendee.position,
      phone: attendee.phone,
      is_vip: attendee.is_vip,
      photo_url: photoUrl,
      photo_key: Date.now(), // Force image reload by changing the key
      has_face_encoding: !!attendee.face_encoding
    })
    setShowForm(true)
  }

  // Delete attendee
  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this attendee?')) {
      try {
        await api.delete(`/api/attendees/${id}`)
        fetchAttendees()
      } catch (err) {
        setError('Failed to delete attendee')
      }
    }
  }

  // Cancel form
  const handleCancel = () => {
    setShowForm(false)
    setEditingAttendee(null)
    setFormData({
      first_name: '',
      last_name: '',
      email: '',
      company: '',
      position: '',
      phone: '',
      is_vip: false,
      photo_url: ''
    })
  }

  useEffect(() => {
    fetchAttendees()
  }, [])

  return (
    <div className="attendee-manager">
      <div className="section-header">
        <h2>Manage Attendees</h2>
        <button 
          className="btn btn-primary"
          onClick={() => setShowForm(true)}
        >
          Add New Attendee
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
          <button onClick={() => setError(null)} className="close-btn">×</button>
        </div>
      )}

      {/* Attendee Form */}
      {showForm && (
        <div className="form-overlay">
          <div className="form-container">
            <h3>{editingAttendee ? 'Edit Attendee' : 'Add New Attendee'}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-grid">
                <div className="form-group">
                  <label>First Name *</label>
                  <input
                    type="text"
                    name="first_name"
                    value={formData.first_name}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Last Name *</label>
                  <input
                    type="text"
                    name="last_name"
                    value={formData.last_name}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Email *</label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Company</label>
                  <input
                    type="text"
                    name="company"
                    value={formData.company}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="form-group">
                  <label>Position</label>
                  <input
                    type="text"
                    name="position"
                    value={formData.position}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="form-group">
                  <label>Phone</label>
                  <input
                    type="tel"
                    name="phone"
                    value={formData.phone}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      name="is_vip"
                      checked={formData.is_vip}
                      onChange={handleInputChange}
                    />
                    VIP Attendee
                  </label>
                </div>
                <div className="form-group full-width">
                  <label>Face Photo</label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileUpload}
                  />
                  {formData.photo_url && (
                    <div className="photo-preview">
                      <img 
                        key={formData.photo_key} 
                        src={formData.photo_url} 
                        alt="Preview" 
                        style={{ maxWidth: '200px', maxHeight: '200px' }} 
                      />
                    </div>
                  )}
                </div>
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={handleCancel}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? 'Saving...' : (editingAttendee ? 'Update' : 'Create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Attendees List */}
      <div className="attendees-list">
        {loading && !showForm ? (
          <div className="loading">Loading attendees...</div>
        ) : (
          <div className="table-container">
            <table className="attendees-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Company</th>
                  <th>Position</th>
                  <th>Phone</th>
                  <th>VIP</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {attendees.map(attendee => (
                  <tr key={attendee.id}>
                    <td>
                      <div className="attendee-name">
                        {attendee.first_name} {attendee.last_name}
                      </div>
                    </td>
                    <td>{attendee.email}</td>
                    <td>{attendee.company}</td>
                    <td>{attendee.position}</td>
                    <td>{attendee.phone}</td>
                    <td>
                      {attendee.is_vip ? (
                        <span className="vip-badge">VIP</span>
                      ) : (
                        <span className="regular-badge">Regular</span>
                      )}
                    </td>
                    <td>
                      <span className={`status-badge status-${attendee.status}`}>
                        {attendee.status}
                      </span>
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button 
                          className="btn btn-sm btn-secondary"
                          onClick={() => handleEdit(attendee)}
                        >
                          Edit
                        </button>
                        <button 
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDelete(attendee.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {attendees.length === 0 && (
              <div className="empty-state">
                No attendees found. Click "Add New Attendee" to get started.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default AttendeeManager
