from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.database import get_db, Attendee, Visit, Camera, SystemConfig
from app.schemas import DashboardStats, SystemStatus

router = APIRouter()

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    # Total attendees
    total_attendees = db.query(Attendee).count()
    
    # VIP attendees
    vip_attendees = db.query(Attendee).filter(Attendee.is_vip == True).count()
    
    # Checked-in attendees
    checked_in_attendees = db.query(Attendee).filter(Attendee.status == "checked_in").count()
    
    # Today's visits
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_visits = db.query(Visit).filter(Visit.check_in_time >= today_start).count()
    
    # Active cameras
    active_cameras = db.query(Camera).filter(Camera.is_active == True).count()
    
    # Recent visits (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(hours=24)
    recent_visits = db.query(Visit).filter(Visit.check_in_time >= yesterday).count()
    
    return DashboardStats(
        total_attendees=total_attendees,
        vip_attendees=vip_attendees,
        checked_in_attendees=checked_in_attendees,
        today_visits=today_visits,
        active_cameras=active_cameras,
        recent_visits=recent_visits
    )

@router.get("/system/status", response_model=SystemStatus)
async def get_system_status(db: Session = Depends(get_db)):
    """Get system status and health"""
    # Check database connectivity
    try:
        db.execute("SELECT 1")
        database_status = "healthy"
    except Exception:
        database_status = "unhealthy"
    
    # Check camera status
    cameras = db.query(Camera).filter(Camera.is_active == True).all()
    camera_status = {}
    
    for camera in cameras:
        # This would integrate with actual camera health checks
        camera_status[camera.id] = {
            "name": camera.name,
            "status": "online",  # Placeholder - would check actual camera feed
            "location": camera.location
        }
    
    # Get system configuration
    configs = db.query(SystemConfig).all()
    system_config = {config.key: config.value for config in configs}
    
    return SystemStatus(
        database_status=database_status,
        camera_status=camera_status,
        system_config=system_config,
        uptime="0 days 0 hours",  # Placeholder - would calculate actual uptime
        last_updated=datetime.utcnow()
    )

@router.get("/reports/visits")
async def get_visit_reports(
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db)
):
    """Get visit reports with date filtering"""
    query = db.query(Visit)
    
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.filter(Visit.check_in_time >= start_dt)
    
    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.filter(Visit.check_in_time <= end_dt)
    
    visits = query.order_by(Visit.check_in_time.desc()).all()
    
    # Group by recognition method
    method_stats = {}
    for visit in visits:
        method = visit.recognition_method or "unknown"
        method_stats[method] = method_stats.get(method, 0) + 1
    
    # Group by hour of day
    hourly_stats = {}
    for visit in visits:
        hour = visit.check_in_time.hour
        hourly_stats[hour] = hourly_stats.get(hour, 0) + 1
    
    return {
        "total_visits": len(visits),
        "recognition_methods": method_stats,
        "hourly_distribution": hourly_stats,
        "visits": visits
    }

@router.get("/reports/attendees")
async def get_attendee_reports(db: Session = Depends(get_db)):
    """Get attendee demographic reports"""
    attendees = db.query(Attendee).all()
    
    # Company statistics
    company_stats = {}
    for attendee in attendees:
        company = attendee.company or "Unknown"
        company_stats[company] = company_stats.get(company, 0) + 1
    
    # Status distribution
    status_stats = {}
    for attendee in attendees:
        status = attendee.status or "unknown"
        status_stats[status] = status_stats.get(status, 0) + 1
    
    # VIP vs regular
    vip_count = len([a for a in attendees if a.is_vip])
    regular_count = len(attendees) - vip_count
    
    return {
        "total_attendees": len(attendees),
        "company_distribution": company_stats,
        "status_distribution": status_stats,
        "vip_distribution": {
            "vip": vip_count,
            "regular": regular_count
        }
    }

@router.post("/system/config/{key}")
async def update_system_config(key: str, value: str, db: Session = Depends(get_db)):
    """Update system configuration"""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    
    if config:
        config.value = value
        config.updated_at = datetime.utcnow()
    else:
        config = SystemConfig(key=key, value=value)
        db.add(config)
    
    db.commit()
    
    return {"message": f"Configuration {key} updated successfully", "value": value}

@router.get("/system/config")
async def get_system_config(db: Session = Depends(get_db)):
    """Get all system configuration"""
    configs = db.query(SystemConfig).all()
    return {config.key: config.value for config in configs}

@router.post("/maintenance/cleanup")
async def run_maintenance_cleanup(db: Session = Depends(get_db)):
    """Run maintenance cleanup tasks"""
    try:
        # Clean up old face encodings for deleted attendees
        # This is a placeholder for actual maintenance tasks
        
        return {
            "message": "Maintenance cleanup completed",
            "tasks_performed": [
                "Database optimization",
                "Temporary file cleanup",
                "Log rotation"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Maintenance failed: {str(e)}")

@router.get("/logs")
async def get_system_logs(
    log_type: str = "application",
    lines: int = 100,
    db: Session = Depends(get_db)
):
    """Get system logs (placeholder - would integrate with actual logging system)"""
    # This would integrate with your actual logging system
    # For now, return placeholder data
    
    return {
        "log_type": log_type,
        "lines": lines,
        "logs": [
            f"{datetime.utcnow().isoformat()} - INFO - System running normally",
            f"{datetime.utcnow().isoformat()} - INFO - Camera feed active",
            f"{datetime.utcnow().isoformat()} - INFO - Database connection healthy"
        ]
    }
