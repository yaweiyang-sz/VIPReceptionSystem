-- VIP Reception System Database Initialization Script
-- Creates initial tables and sample data

-- Create extension for UUID if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Insert default system configuration
INSERT INTO system_config (key, value, description) VALUES
('system_name', 'VIP Reception System', 'Name of the system'),
('version', '1.0.0', 'System version'),
('recognition_threshold', '0.6', 'Face recognition confidence threshold'),
('auto_recognition', 'true', 'Enable automatic recognition'),
('camera_health_check_interval', '30', 'Camera health check interval in seconds'),
('max_attendee_photo_size', '5242880', 'Maximum photo size in bytes (5MB)')
ON CONFLICT (key) DO NOTHING;

-- Insert sample cameras
INSERT INTO cameras (name, source, location, resolution, fps, is_active) VALUES
('Webcam Test Camera', '0', 'Test Area', '1920x1080', 30, true),
('Public Test Stream', 'https://www.rmp-streaming.com/media/big-buck-bunny-360p.mp4', 'Demo Area', '640x360', 30, true),
('RTSP Test Stream', 'rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4', 'Demo Area', '640x360', 30, true),
('Local Test Camera', 'http://localhost:8080/video', 'Local Test', '1280x720', 25, true)
ON CONFLICT DO NOTHING;

-- Insert sample attendees
INSERT INTO attendees (first_name, last_name, email, company, position, phone, is_vip, qr_code, status) VALUES
('John', 'Smith', 'john.smith@aviation.com', 'Sky Airlines', 'CEO', '+1-555-0101', true, '550e8400-e29b-41d4-a716-446655440000', 'registered'),
('Sarah', 'Johnson', 'sarah.johnson@aerotech.com', 'AeroTech Industries', 'CTO', '+1-555-0102', true, '550e8400-e29b-41d4-a716-446655440001', 'registered'),
('Michael', 'Chen', 'michael.chen@flyhigh.com', 'FlyHigh Aviation', 'VP of Operations', '+1-555-0103', false, '550e8400-e29b-41d4-a716-446655440002', 'registered'),
('Emily', 'Davis', 'emily.davis@jetstream.com', 'JetStream Airlines', 'Marketing Director', '+1-555-0104', false, '550e8400-e29b-41d4-a716-446655440003', 'registered'),
('Robert', 'Wilson', 'robert.wilson@airlux.com', 'AirLux Interiors', 'Design Manager', '+1-555-0105', true, '550e8400-e29b-41d4-a716-446655440004', 'registered')
ON CONFLICT DO NOTHING;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_attendees_email ON attendees(email);
CREATE INDEX IF NOT EXISTS idx_attendees_qr_code ON attendees(qr_code);
CREATE INDEX IF NOT EXISTS idx_attendees_status ON attendees(status);
CREATE INDEX IF NOT EXISTS idx_attendees_is_vip ON attendees(is_vip);
CREATE INDEX IF NOT EXISTS idx_visits_attendee_id ON visits(attendee_id);
CREATE INDEX IF NOT EXISTS idx_visits_check_in_time ON visits(check_in_time);
CREATE INDEX IF NOT EXISTS idx_visits_camera_id ON visits(camera_id);
CREATE INDEX IF NOT EXISTS idx_cameras_is_active ON cameras(is_active);
CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(key);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_attendees_updated_at ON attendees;
CREATE TRIGGER update_attendees_updated_at
    BEFORE UPDATE ON attendees
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_system_config_updated_at ON system_config;
CREATE TRIGGER update_system_config_updated_at
    BEFORE UPDATE ON system_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
