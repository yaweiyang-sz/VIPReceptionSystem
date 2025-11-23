import asyncio
import time
import logging
import pickle
import base64
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import cv2
import numpy as np
import requests

from app.database import Attendee
from app.recognition_engine import face_recognition_engine

logger = logging.getLogger(__name__)

class BatchFaceProcessor:
    """Batch processor for handling large numbers of face encodings efficiently"""
    
    def __init__(self):
        self.batch_size = 10  # Process 10 images at a time
        self.max_workers = 4  # Number of concurrent encoding processes
        self.timeout = 30  # Timeout for image downloads
        self.retry_attempts = 3
        
    async def process_attendee_batch(self, db: Session, attendee_ids: List[int]) -> Dict[str, Any]:
        """Process a batch of attendees for face encoding"""
        try:
            start_time = time.time()
            results = {
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
                'errors': [],
                'processing_time': 0
            }
            
            # Get attendees from database
            attendees = db.query(Attendee).filter(Attendee.id.in_(attendee_ids)).all()
            
            if not attendees:
                logger.warning("No attendees found for batch processing")
                return results
            
            logger.info(f"Processing batch of {len(attendees)} attendees")
            
            # Process in smaller sub-batches
            sub_batch_size = 5
            for i in range(0, len(attendees), sub_batch_size):
                sub_batch = attendees[i:i + sub_batch_size]
                sub_batch_results = await self._process_sub_batch(db, sub_batch)
                
                results['total_processed'] += sub_batch_results['total_processed']
                results['successful'] += sub_batch_results['successful']
                results['failed'] += sub_batch_results['failed']
                results['errors'].extend(sub_batch_results['errors'])
                
                # Small delay between sub-batches to avoid overwhelming the system
                await asyncio.sleep(0.1)
            
            results['processing_time'] = time.time() - start_time
            logger.info(f"Batch processing completed: {results['successful']} successful, {results['failed']} failed in {results['processing_time']:.2f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            results['errors'].append(str(e))
            return results
    
    async def _process_sub_batch(self, db: Session, attendees: List[Attendee]) -> Dict[str, Any]:
        """Process a sub-batch of attendees"""
        results = {
            'total_processed': len(attendees),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        tasks = []
        for attendee in attendees:
            task = self._process_single_attendee(db, attendee)
            tasks.append(task)
        
        # Process concurrently with limited workers
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def bounded_task(task):
            async with semaphore:
                return await task
        
        batch_results = await asyncio.gather(*[bounded_task(task) for task in tasks], return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                results['failed'] += 1
                results['errors'].append(str(result))
            elif result.get('success'):
                results['successful'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(result.get('error', 'Unknown error'))
        
        return results
    
    async def _process_single_attendee(self, db: Session, attendee: Attendee) -> Dict[str, Any]:
        """Process a single attendee for face encoding"""
        try:
            # Check if attendee already has face encoding
            if attendee.face_encoding and attendee.face_encoding.strip():
                logger.debug(f"Attendee {attendee.id} already has face encoding, skipping")
                return {'success': True, 'attendee_id': attendee.id, 'action': 'skipped'}
            
            # Check if photo URL is available
            if not attendee.photo_url or not attendee.photo_url.strip():
                logger.warning(f"Attendee {attendee.id} has no photo URL")
                return {'success': False, 'attendee_id': attendee.id, 'error': 'No photo URL available'}
            
            # Download and process image
            image_data = await self._download_image(attendee.photo_url)
            if not image_data:
                return {'success': False, 'attendee_id': attendee.id, 'error': 'Failed to download image'}
            
            # Encode face
            encoding_results = await face_recognition_engine.encode_face(image_data)
            if not encoding_results:
                return {'success': False, 'attendee_id': attendee.id, 'error': 'No face detected in image'}
            
            # Use the first face found
            encoding_result = encoding_results[0]
            
            # Update attendee record
            attendee.face_encoding = encoding_result['encoding']
            attendee.face_encoding_version = "v1"
            attendee.face_encoding_quality = "standard"
            attendee.face_encoding_created = time.time()
            
            # Update in-memory cache
            metadata = {
                'name': f"{attendee.first_name} {attendee.last_name}",
                'company': attendee.company,
                'is_vip': attendee.is_vip,
                'last_updated': time.time()
            }
            face_recognition_engine.update_known_faces(attendee.id, encoding_result['encoding'], metadata)
            
            db.commit()
            
            logger.info(f"Successfully encoded face for attendee {attendee.id}")
            return {'success': True, 'attendee_id': attendee.id, 'action': 'encoded'}
            
        except Exception as e:
            logger.error(f"Error processing attendee {attendee.id}: {e}")
            db.rollback()
            return {'success': False, 'attendee_id': attendee.id, 'error': str(e)}
    
    async def _download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                response = requests.get(url, timeout=self.timeout, stream=True)
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"URL {url} does not point to an image (content-type: {content_type})")
                    return None
                
                # Read image data
                image_data = response.content
                
                # Verify it's a valid image
                try:
                    nparr = np.frombuffer(image_data, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if image is None:
                        logger.warning(f"Downloaded data from {url} is not a valid image")
                        continue
                except Exception as e:
                    logger.warning(f"Invalid image data from {url}: {e}")
                    continue
                
                return image_data
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed to download {url}: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(1)  # Wait before retry
                continue
            except Exception as e:
                logger.error(f"Unexpected error downloading {url}: {e}")
                break
        
        return None
    
    async def validate_encodings(self, db: Session, attendee_ids: List[int] = None) -> Dict[str, Any]:
        """Validate existing face encodings"""
        try:
            query = db.query(Attendee).filter(Attendee.face_encoding.isnot(None))
            if attendee_ids:
                query = query.filter(Attendee.id.in_(attendee_ids))
            
            attendees = query.all()
            
            results = {
                'total_checked': len(attendees),
                'valid': 0,
                'invalid': 0,
                'errors': []
            }
            
            for attendee in attendees:
                try:
                    # Try to decode the encoding
                    encoding_bytes = base64.b64decode(attendee.face_encoding)
                    encoding = pickle.loads(encoding_bytes)
                    
                    # Check if it's a valid numpy array
                    if isinstance(encoding, np.ndarray) and encoding.shape == (128,):
                        results['valid'] += 1
                    else:
                        results['invalid'] += 1
                        results['errors'].append(f"Invalid encoding format for attendee {attendee.id}")
                        
                except Exception as e:
                    results['invalid'] += 1
                    results['errors'].append(f"Error decoding encoding for attendee {attendee.id}: {e}")
            
            logger.info(f"Encoding validation completed: {results['valid']} valid, {results['invalid']} invalid")
            return results
            
        except Exception as e:
            logger.error(f"Error in encoding validation: {e}")
            return {'total_checked': 0, 'valid': 0, 'invalid': 0, 'errors': [str(e)]}
    
    def get_statistics(self, db: Session) -> Dict[str, Any]:
        """Get statistics about face encodings in the system"""
        try:
            total_attendees = db.query(Attendee).count()
            attendees_with_encoding = db.query(Attendee).filter(Attendee.face_encoding.isnot(None)).count()
            vip_attendees = db.query(Attendee).filter(Attendee.is_vip == True).count()
            vip_with_encoding = db.query(Attendee).filter(
                Attendee.is_vip == True, 
                Attendee.face_encoding.isnot(None)
            ).count()
            
            stats = {
                'total_attendees': total_attendees,
                'attendees_with_face_encoding': attendees_with_encoding,
                'encoding_coverage_percentage': round((attendees_with_encoding / total_attendees * 100) if total_attendees > 0 else 0, 2),
                'vip_attendees': vip_attendees,
                'vip_with_encoding': vip_with_encoding,
                'vip_coverage_percentage': round((vip_with_encoding / vip_attendees * 100) if vip_attendees > 0 else 0, 2),
                'face_cache_size': face_recognition_engine.face_cache_size,
                'face_cache_loaded': face_recognition_engine.face_cache_loaded,
                'last_cache_update': face_recognition_engine.last_cache_update
            }
            
            # Add performance stats
            perf_stats = face_recognition_engine.get_performance_stats()
            stats.update(perf_stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'error': str(e)}

# Global instance
batch_processor = BatchFaceProcessor()
