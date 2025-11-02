"""Service for storing and retrieving people discoveries"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from src.models.person import Person
from src.db.supabase_client import get_client
from src.db.models import PersonDiscovery, person_to_discovery

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Service for managing people discoveries"""
    
    @staticmethod
    def save_discoveries(
        job_id: Optional[UUID],
        user_id: Optional[UUID],
        people: List[Person],
        relevance_scores: Optional[Dict[str, float]] = None,
        match_reasons: Optional[Dict[str, List[str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Save people discoveries to database.
        
        Args:
            job_id: Job ID (optional)
            user_id: User ID (optional)
            people: List of Person objects to save
            relevance_scores: Optional dict mapping person name to relevance score
            match_reasons: Optional dict mapping person name to match reasons
            
        Returns:
            List of saved PersonDiscovery records
        """
        client = get_client()
        
        if not people:
            return []
        
        discoveries_to_insert = []
        
        for person in people:
            try:
                # Validate person has required fields
                if not person.name:
                    logger.warning(f"Skipping person with no name: {person}")
                    continue
                
                # Calculate relevance score
                relevance_score = None
                if relevance_scores and person.name in relevance_scores:
                    relevance_score = relevance_scores[person.name]
                
                # Get match reasons
                person_match_reasons = None
                if match_reasons and person.name in match_reasons:
                    person_match_reasons = match_reasons[person.name]
                
                # Convert Person to PersonDiscovery dict
                discovery_dict = person_to_discovery(
                    person=person,
                    job_id=job_id,
                    user_id=user_id,
                    relevance_score=relevance_score,
                    match_reasons=person_match_reasons
                )
                
                discoveries_to_insert.append(discovery_dict)
            except Exception as e:
                logger.error(f"Error converting person {person.name if person.name else 'unknown'} to discovery: {e}")
                continue
        
        # Batch insert
        if discoveries_to_insert:
            # Insert in batches of 100 (Supabase limit)
            batch_size = 100
            all_results = []
            failed_count = 0
            
            for i in range(0, len(discoveries_to_insert), batch_size):
                batch = discoveries_to_insert[i:i + batch_size]
                
                try:
                    result = client.table('people_discoveries').insert(batch).execute()
                    if result.data:
                        all_results.extend(result.data)
                        logger.info(f"Successfully inserted batch of {len(result.data)} discoveries")
                    else:
                        logger.warning(f"Batch insert returned no data (batch {i // batch_size + 1})")
                except Exception as e:
                    failed_count += len(batch)
                    error_msg = str(e)
                    logger.error(f"Error inserting batch {i // batch_size + 1}: {error_msg}")
                    
                    # If it's a column error, log the columns we're trying to insert
                    if 'column' in error_msg.lower() or 'PGRST' in error_msg:
                        logger.error(f"Batch columns: {list(batch[0].keys()) if batch else 'empty'}")
                        # Try inserting without optional fields that might not exist
                        try:
                            safe_batch = []
                            for item in batch:
                                safe_item = {k: v for k, v in item.items() 
                                            if k in ['job_id', 'user_id', 'person_type', 'full_name', 
                                                    'title', 'email', 'linkedin_url', 'confidence_score',
                                                    'connection_path', 'contacted']}
                                safe_batch.append(safe_item)
                            if safe_batch:
                                result = client.table('people_discoveries').insert(safe_batch).execute()
                                if result.data:
                                    all_results.extend(result.data)
                                    logger.info(f"Successfully inserted safe batch of {len(result.data)} discoveries")
                        except Exception as retry_error:
                            logger.error(f"Retry with safe columns also failed: {retry_error}")
                    
                    # Continue with next batch
                    
            if failed_count > 0:
                logger.warning(f"Failed to insert {failed_count} out of {len(discoveries_to_insert)} discoveries")
            
            logger.info(f"Successfully saved {len(all_results)} discoveries to database")
            return all_results
        
        return []
    
    @staticmethod
    def get_discoveries_for_job(
        job_id: UUID,
        user_id: Optional[UUID] = None,
        person_type: Optional[str] = None
    ) -> List[PersonDiscovery]:
        """Get all discoveries for a job"""
        client = get_client()
        
        try:
            query = client.table('people_discoveries').select('*').eq('job_id', str(job_id))
            
            if user_id:
                query = query.eq('user_id', str(user_id))
            
            if person_type:
                query = query.eq('person_type', person_type)
            
            result = query.order('created_at', desc=True).execute()
            
            if result.data:
                discoveries = []
                for record in result.data:
                    try:
                        discoveries.append(PersonDiscovery(**record))
                    except Exception as e:
                        logger.warning(f"Failed to parse discovery record: {e}, record: {record}")
                return discoveries
            
            return []
        except Exception as e:
            logger.error(f"Error fetching discoveries for job {job_id}: {e}")
            return []
    
    @staticmethod
    def get_discovery_by_id(discovery_id: UUID) -> Optional[PersonDiscovery]:
        """Get a single discovery by ID"""
        client = get_client()
        
        try:
            result = client.table('people_discoveries').select('*').eq('id', str(discovery_id)).execute()
            
            if result.data:
                try:
                    return PersonDiscovery(**result.data[0])
                except Exception as e:
                    logger.error(f"Failed to parse discovery record: {e}, record: {result.data[0]}")
                    return None
            
            return None
        except Exception as e:
            logger.error(f"Error fetching discovery {discovery_id}: {e}")
            return None
    
    @staticmethod
    def mark_contacted(discovery_id: UUID, notes: Optional[str] = None) -> bool:
        """Mark a discovery as contacted"""
        client = get_client()
        
        try:
            update_data = {'contacted': True}
            if notes:
                update_data['notes'] = notes
            
            result = client.table('people_discoveries').update(update_data).eq('id', str(discovery_id)).execute()
            
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error marking discovery {discovery_id} as contacted: {e}")
            return False
    
    @staticmethod
    def get_discoveries_for_user(
        user_id: UUID,
        limit: int = 100
    ) -> List[PersonDiscovery]:
        """Get all discoveries for a user"""
        client = get_client()
        
        try:
            result = client.table('people_discoveries').select('*').eq('user_id', str(user_id)).order('created_at', desc=True).limit(limit).execute()
            
            if result.data:
                discoveries = []
                for record in result.data:
                    try:
                        discoveries.append(PersonDiscovery(**record))
                    except Exception as e:
                        logger.warning(f"Failed to parse discovery record: {e}, record: {record}")
                return discoveries
            
            return []
        except Exception as e:
            logger.error(f"Error fetching discoveries for user {user_id}: {e}")
            return []

