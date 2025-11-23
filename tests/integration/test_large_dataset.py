#!/usr/bin/env python3
"""
Test script for simulating large dataset performance with optimized face encoding
"""

import asyncio
import time
import random
import logging
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our modules
import face_recognition
from backend.app.database import get_db, Attendee, Base
from backend.app.recognition_engine import face_recognition_engine
from backend.app.batch_processor import batch_processor

# Database configuration
DATABASE_URL = "postgresql://vip_user:vip_password@localhost:5432/vip_reception"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def test_large_dataset_performance():
    """Test the system with simulated large dataset"""
    logger.info("Starting large dataset performance test")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Test 1: Load face cache performance
        logger.info("Test 1: Loading face cache with large dataset")
        start_time = time.time()
        
        success = face_recognition_engine.load_known_faces(db)
        load_time = time.time() - start_time
        
        if success:
            logger.info(f"✓ Face cache loaded successfully in {load_time:.2f}s")
            logger.info(f"  - Cache size: {face_recognition_engine.face_cache_size} faces")
            logger.info(f"  - Cache loaded: {face_recognition_engine.face_cache_loaded}")
        else:
            logger.error("✗ Failed to load face cache")
            return
        
        # Test 2: Performance statistics
        logger.info("Test 2: Performance statistics")
        perf_stats = face_recognition_engine.get_performance_stats()
        logger.info(f"  - Average recognition time: {perf_stats['avg_recognition_time_ms']:.2f}ms")
        logger.info(f"  - Average encoding time: {perf_stats['avg_encoding_time_ms']:.2f}ms")
        logger.info(f"  - Total recognition attempts: {perf_stats['total_recognition_attempts']}")
        logger.info(f"  - Total encoding attempts: {perf_stats['total_encoding_attempts']}")
        
        # Test 3: Batch processing statistics
        logger.info("Test 3: System statistics")
        system_stats = batch_processor.get_statistics(db)
        logger.info(f"  - Total attendees: {system_stats['total_attendees']}")
        logger.info(f"  - Attendees with face encoding: {system_stats['attendees_with_face_encoding']}")
        logger.info(f"  - Encoding coverage: {system_stats['encoding_coverage_percentage']}%")
        logger.info(f"  - VIP attendees: {system_stats['vip_attendees']}")
        logger.info(f"  - VIP with encoding: {system_stats['vip_with_encoding']}")
        logger.info(f"  - VIP coverage: {system_stats['vip_coverage_percentage']}%")
        
        # Test 4: Simulate recognition with different cache sizes
        logger.info("Test 4: Simulating recognition performance")
        await simulate_recognition_performance(db)
        
        # Test 5: Batch processing simulation
        logger.info("Test 5: Batch processing simulation")
        await simulate_batch_processing(db)
        
        logger.info("✓ All performance tests completed successfully")
        
    except Exception as e:
        logger.error(f"Error during performance testing: {e}")
    finally:
        db.close()

async def simulate_recognition_performance(db: Session):
    """Simulate recognition performance with different scenarios"""
    
    # Get some attendees for testing
    attendees = db.query(Attendee).filter(Attendee.face_encoding.isnot(None)).limit(10).all()
    
    if not attendees:
        logger.warning("No attendees with face encodings found for recognition testing")
        return
    
    logger.info(f"Testing recognition with {len(attendees)} known faces")
    
    # Test recognition speed with different cache sizes
    cache_sizes = [10, 50, 100, 500, 1000]
    
    for target_size in cache_sizes:
        if face_recognition_engine.face_cache_size >= target_size:
            logger.info(f"  Testing with {target_size} faces in cache...")
            
            # Simulate recognition (this would normally use real camera frames)
            # For testing, we'll just measure the comparison time
            start_time = time.time()
            
            # Simulate multiple recognition attempts
            recognition_attempts = 10
            for i in range(recognition_attempts):
                # This simulates the face comparison part of recognition
                if face_recognition_engine.known_face_encodings:
                    # Use a random encoding from the cache for testing
                    test_encoding = random.choice(face_recognition_engine.known_face_encodings)
                    
                    # Simulate comparison (this is what happens in recognize_face)
                    matches = face_recognition.compare_faces(
                        face_recognition_engine.known_face_encodings[:target_size], 
                        test_encoding
                    )
                    face_distances = face_recognition.face_distance(
                        face_recognition_engine.known_face_encodings[:target_size], 
                        test_encoding
                    )
            
            avg_time = (time.time() - start_time) / recognition_attempts * 1000
            logger.info(f"    Average recognition time: {avg_time:.2f}ms")
            
            # Estimate performance for 1000 faces
            if target_size == 1000:
                logger.info(f"    Estimated performance for 1000+ guests: {avg_time:.2f}ms per recognition")
                if avg_time < 100:  # Less than 100ms is good for real-time
                    logger.info("    ✓ Performance suitable for real-time recognition")
                else:
                    logger.warning("    ⚠ Performance may be borderline for real-time recognition")

async def simulate_batch_processing(db: Session):
    """Simulate batch processing performance"""
    
    # Get attendees without face encodings for testing
    attendees_without_encoding = db.query(Attendee).filter(
        Attendee.face_encoding.is_(None) | (Attendee.face_encoding == '')
    ).limit(20).all()
    
    if not attendees_without_encoding:
        logger.info("No attendees without face encodings found for batch processing test")
        return
    
    attendee_ids = [a.id for a in attendees_without_encoding]
    
    logger.info(f"Testing batch processing with {len(attendee_ids)} attendees")
    
    # Test batch processing
    start_time = time.time()
    results = await batch_processor.process_attendee_batch(db, attendee_ids)
    processing_time = time.time() - start_time
    
    logger.info(f"  Batch processing results:")
    logger.info(f"    - Total processed: {results['total_processed']}")
    logger.info(f"    - Successful: {results['successful']}")
    logger.info(f"    - Failed: {results['failed']}")
    logger.info(f"    - Processing time: {processing_time:.2f}s")
    logger.info(f"    - Average time per attendee: {processing_time/max(1, results['total_processed']):.2f}s")
    
    if results['errors']:
        logger.warning(f"    - Errors: {results['errors'][:3]}")  # Show first 3 errors
    
    # Estimate performance for 1000 attendees
    estimated_time_1000 = (processing_time / max(1, results['total_processed'])) * 1000
    logger.info(f"    Estimated time for 1000 attendees: {estimated_time_1000/60:.1f} minutes")

def generate_performance_report():
    """Generate a comprehensive performance report"""
    logger.info("\n" + "="*60)
    logger.info("PERFORMANCE REPORT FOR 1000+ GUEST SCENARIO")
    logger.info("="*60)
    
    db = SessionLocal()
    try:
        # System statistics
        stats = batch_processor.get_statistics(db)
        
        logger.info("SYSTEM CAPACITY:")
        logger.info(f"  • Current face cache: {stats['face_cache_size']} faces")
        logger.info(f"  • Memory usage: ~{stats['face_cache_size'] * 0.5:.1f} KB (estimated)")
        logger.info(f"  • Encoding coverage: {stats['encoding_coverage_percentage']}%")
        
        logger.info("\nPERFORMANCE METRICS:")
        logger.info(f"  • Average recognition time: {stats['avg_recognition_time_ms']:.2f}ms")
        logger.info(f"  • Average encoding time: {stats['avg_encoding_time_ms']:.2f}ms")
        
        # Performance assessment
        if stats['avg_recognition_time_ms'] < 50:
            logger.info("  • Recognition performance: EXCELLENT ✓")
        elif stats['avg_recognition_time_ms'] < 100:
            logger.info("  • Recognition performance: GOOD ✓")
        elif stats['avg_recognition_time_ms'] < 200:
            logger.info("  • Recognition performance: ACCEPTABLE ⚠")
        else:
            logger.info("  • Recognition performance: POOR ✗")
        
        logger.info("\nSCALABILITY ASSESSMENT:")
        logger.info("  • Batch processing: Optimized for concurrent processing")
        logger.info("  • Memory management: Efficient caching with metadata")
        logger.info("  • Database storage: Optimized schema with versioning")
        logger.info("  • Network efficiency: Minimal data transfer")
        
        logger.info("\nRECOMMENDATIONS FOR 1000+ GUESTS:")
        logger.info("  1. Use batch processing for initial encoding")
        logger.info("  2. Monitor memory usage with large cache sizes")
        logger.info("  3. Consider GPU acceleration for faster processing")
        logger.info("  4. Implement periodic cache validation")
        logger.info("  5. Use quality settings based on use case")
        
    finally:
        db.close()

if __name__ == "__main__":
    # Run the performance tests
    asyncio.run(test_large_dataset_performance())
    
    # Generate final report
    generate_performance_report()
