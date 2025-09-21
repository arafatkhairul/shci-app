"""
Session Management Service
"""
import time
import uuid
from typing import Optional, Dict, Any
from app.models.session_memory import SessionMemory, MemoryStore
from app.utils.logger import get_logger

log = get_logger("session_service")

class SessionService:
    """Service for managing user sessions without authentication"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = 1200  # 20 minutes
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def create_session(self, connection_id: str) -> str:
        """Create a new session for a connection"""
        session_id = f"session_{connection_id}_{int(time.time())}"
        
        # Create session memory
        memory = SessionMemory()
        memory.client_id = session_id
        memory.session_start_time = time.time()
        
        # Store session info
        self.active_sessions[session_id] = {
            "connection_id": connection_id,
            "memory": memory,
            "last_activity": time.time(),
            "created_at": time.time()
        }
        
        log.info(f"🆕 Created new session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        return self.active_sessions.get(session_id)
    
    def load_session_memory(self, session_id: str) -> Optional[SessionMemory]:
        """Load session memory from database"""
        try:
            memory_store = MemoryStore(session_id)
            memory_data = memory_store.load()
            
            if memory_data:
                memory = SessionMemory()
                memory.load_from_dict(memory_data)
                memory.client_id = session_id
                return memory
            return None
            
        except Exception as e:
            log.error(f"Error loading session memory for {session_id}: {e}")
            return None
    
    def save_session_memory(self, session_id: str, memory: SessionMemory) -> bool:
        """Save session memory to database"""
        try:
            memory_store = MemoryStore(session_id)
            memory_store.save(memory)
            return True
        except Exception as e:
            log.error(f"Error saving session memory for {session_id}: {e}")
            return False
    
    def update_session_activity(self, session_id: str):
        """Update last activity time for session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = time.time()
    
    def is_session_active(self, session_id: str) -> bool:
        """Check if session is still active"""
        if session_id not in self.active_sessions:
            return False
        
        current_time = time.time()
        last_activity = self.active_sessions[session_id]["last_activity"]
        
        return (current_time - last_activity) < self.session_timeout
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = time.time()
        
        # Only cleanup every 5 minutes
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        expired_sessions = []
        for session_id, session_data in self.active_sessions.items():
            if (current_time - session_data["last_activity"]) > self.session_timeout:
                expired_sessions.append(session_id)
        
        # Remove expired sessions
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
            log.info(f"🧹 Cleaned up expired session: {session_id}")
        
        self.last_cleanup = current_time
        
        if expired_sessions:
            log.info(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        current_time = time.time()
        active_count = 0
        total_interactions = 0
        
        for session_data in self.active_sessions.values():
            if (current_time - session_data["last_activity"]) < self.session_timeout:
                active_count += 1
                if hasattr(session_data["memory"], 'total_interactions'):
                    total_interactions += session_data["memory"].total_interactions
        
        return {
            "active_sessions": active_count,
            "total_sessions": len(self.active_sessions),
            "total_interactions": total_interactions,
            "session_timeout": self.session_timeout,
            "last_cleanup": self.last_cleanup
        }
    
    def get_session_by_connection(self, connection_id: str) -> Optional[str]:
        """Get session ID by connection ID"""
        for session_id, session_data in self.active_sessions.items():
            if session_data["connection_id"] == connection_id:
                return session_id
        return None
    
    def create_or_get_session(self, connection_id: str) -> str:
        """Create new session or get existing one for connection"""
        # First try to find existing session
        existing_session = self.get_session_by_connection(connection_id)
        if existing_session and self.is_session_active(existing_session):
            self.update_session_activity(existing_session)
            return existing_session
        
        # Create new session
        return self.create_session(connection_id)

# Global session service instance
session_service = SessionService()

