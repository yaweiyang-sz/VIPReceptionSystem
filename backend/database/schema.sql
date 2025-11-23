-- VIP Reception System Database Schema
-- Creates all tables with proper column definitions

-- Create extension for UUID if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS visits CASCADE;
DROP TABLE IF EXISTS attendees CASCADE;
DROP TABLE IF EXISTS cameras CASCADE;
DROP TABLE IF EXISTS system_config CASCADE;

-- Create attendees table
CREATE TABLE attendees (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    company VARCHAR(255),
    position VARCHAR(255),
    phone VARCHAR(50),
    photo_url TEXT,
    face_encoding TEXT,
    face_encoding_version VARCHAR(10) DEFAULT 'v1',
    face_encoding_quality VARCHAR(20) DEFAULT 'standard',
    face_encoding_created TIMESTAMP WITH TIME ZONE,
    qr_code VARCHAR(100) UNIQUE,
    is_vip BOOLEAN DEFAULT false,
    status VARCHAR(50) DEFAULT 'registered',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create cameras table
CREATE TABLE cameras (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    source VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    resolution VARCHAR(50) DEFAULT '1920x1080',
    fps INTEGER DEFAULT 30,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create visits table
CREATE TABLE visits (
    id SERIAL PRIMARY KEY,
    attendee_id INTEGER REFERENCES attendees(id),
    check_in_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    check_out_time TIMESTAMP WITH TIME ZONE,
    recognition_method VARCHAR(50),
    camera_id INTEGER REFERENCES cameras(id),
    notes TEXT
);

-- Create system_config table
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for better performance
CREATE INDEX idx_attendees_email ON attendees(email);
CREATE INDEX idx_attendees_qr_code ON attendees(qr_code);
CREATE INDEX idx_attendees_status ON attendees(status);
CREATE INDEX idx_attendees_is_vip ON attendees(is_vip);
CREATE INDEX idx_visits_attendee_id ON visits(attendee_id);
CREATE INDEX idx_visits_check_in_time ON visits(check_in_time);
CREATE INDEX idx_visits_camera_id ON visits(camera_id);
CREATE INDEX idx_cameras_is_active ON cameras(is_active);
CREATE INDEX idx_system_config_key ON system_config(key);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_attendees_updated_at
    BEFORE UPDATE ON attendees
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at
    BEFORE UPDATE ON system_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
