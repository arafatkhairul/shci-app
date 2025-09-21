"""
Session Memory Models
"""
import time
import json
import sqlite3
from typing import Optional, Dict, Any, List
from app.config.settings import settings
from app.utils.logger import get_logger

log = get_logger("session_memory")

class SessionMemory:
    """Enhanced session memory management for user interactions with full conversation context"""
    
    def __init__(self, language: str = "en"):
        self.user_name: Optional[str] = None
        self.last_destination: Optional[str] = None
        self.facts: Dict[str, Any] = {}
        self.traits: Dict[str, Any] = {}
        self.history: List[Dict[str, str]] = []
        self.greeted: bool = False
        self.language: str = language
        self.voice: str = "en_US-libritts_r-medium"  # Default voice
        self.client_id: Optional[str] = None
        self.level: str = "medium"
        
        # Enhanced conversation memory
        self.conversation_context: List[Dict[str, Any]] = []  # Full conversation history
        self.session_start_time: float = time.time()
        self.last_interaction_time: float = time.time()
        self.total_interactions: int = 0
        self.conversation_topics: List[str] = []  # Topics discussed
        self.user_preferences: Dict[str, Any] = {}  # User preferences and settings
        
        # Role play configuration
        self.role_play_enabled: bool = False
        self.role_play_template: str = "school"
        self.organization_name: str = ""
        self.organization_details: str = ""
        self.role_title: str = ""
        
        # Recent level change tracking
        self._recent_level_change_ts: Optional[float] = None
        
        # Context isolation for level changes
        self._context_isolation_threshold = 3  # Keep last 3 turns when level changes
        
        # Memory management settings
        self.max_conversation_history: int = 50  # Maximum conversation turns to keep
        self.max_context_length: int = 1000  # Maximum context length for LLM

    def add_history(self, role: str, content: str):
        """Add interaction to history with enhanced context tracking"""
        current_time = time.time()
        
        # Add to basic history
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": current_time
        })
        
        # Add to enhanced conversation context
        self.conversation_context.append({
            "role": role,
            "content": content,
            "timestamp": current_time,
            "interaction_id": self.total_interactions + 1,
            "session_duration": current_time - self.session_start_time
        })
        
        # Update interaction tracking
        self.total_interactions += 1
        self.last_interaction_time = current_time
        
        # Extract topics from user messages for better context
        if role == "user":
            self._extract_topics(content)
        
        # Maintain context isolation if level changed recently
        if self._recent_level_change_ts and current_time - self._recent_level_change_ts < 300:  # 5 minutes
            if len(self.history) > self._context_isolation_threshold:
                self.history = self.history[-self._context_isolation_threshold:]
                self.conversation_context = self.conversation_context[-self._context_isolation_threshold:]
        
        # Manage conversation context size
        self._manage_context_size()

    def get_recent_context(self, max_turns: int = 5) -> List[Dict[str, str]]:
        """Get recent conversation context"""
        return self.history[-max_turns:] if self.history else []
    
    def get_enhanced_context(self, max_turns: int = 10) -> List[Dict[str, Any]]:
        """Get enhanced conversation context with full metadata"""
        return self.conversation_context[-max_turns:] if self.conversation_context else []
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get conversation summary for better context"""
        return {
            "session_duration": time.time() - self.session_start_time,
            "total_interactions": self.total_interactions,
            "topics_discussed": self.conversation_topics[-10:],  # Last 10 topics
            "user_name": self.user_name,
            "language": self.language,
            "voice": self.voice,
            "level": self.level,
            "last_interaction": self.last_interaction_time,
            "conversation_length": len(self.conversation_context)
        }
    
    def _extract_topics(self, content: str):
        """Extract topics from user messages for better context understanding"""
        import re
        
        # Simple topic extraction based on keywords
        content_lower = content.lower()
        
        # Common topic keywords
        topic_keywords = {
            "weather": ["weather", "rain", "sunny", "cloudy", "temperature", "forecast"],
            "work": ["work", "job", "office", "meeting", "project", "business"],
            "food": ["food", "eat", "restaurant", "cooking", "recipe", "hungry"],
            "travel": ["travel", "trip", "vacation", "flight", "hotel", "destination"],
            "technology": ["computer", "phone", "software", "app", "internet", "tech"],
            "health": ["health", "sick", "doctor", "medicine", "exercise", "fitness"],
            "family": ["family", "mother", "father", "sister", "brother", "parents"],
            "education": ["school", "study", "learn", "book", "course", "education"],
            "entertainment": ["movie", "music", "game", "fun", "entertainment", "show"],
            "shopping": ["buy", "shop", "store", "price", "money", "shopping"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                if topic not in self.conversation_topics:
                    self.conversation_topics.append(topic)
                    # Keep only last 20 topics
                    if len(self.conversation_topics) > 20:
                        self.conversation_topics = self.conversation_topics[-20:]
                break
    
    def _manage_context_size(self):
        """Manage conversation context size to prevent memory overflow"""
        # Keep only recent conversation history
        if len(self.conversation_context) > self.max_conversation_history:
            # Keep the most recent conversations
            self.conversation_context = self.conversation_context[-self.max_conversation_history:]
        
        # Also manage basic history
        if len(self.history) > self.max_conversation_history:
            self.history = self.history[-self.max_conversation_history:]
    
    def get_context_for_llm(self, max_length: int = None) -> List[Dict[str, str]]:
        """Get optimized context for LLM with length management"""
        max_length = max_length or self.max_context_length
        
        # Get recent context
        recent_context = self.get_enhanced_context(max_turns=15)
        
        # Convert to LLM format and manage length
        llm_context = []
        current_length = 0
        
        for item in recent_context:
            content = item["content"]
            if current_length + len(content) > max_length:
                break
            
            llm_context.append({
                "role": item["role"],
                "content": content
            })
            current_length += len(content)
        
        return llm_context

    def load_from_dict(self, data: Dict[str, Any]):
        """Load memory from dictionary with enhanced conversation context"""
        self.user_name = data.get("user_name")
        self.last_destination = data.get("last_destination")
        self.facts = data.get("facts", {})
        self.traits = data.get("traits", {})
        self.history = data.get("history", [])
        self.greeted = data.get("greeted", False)
        self.language = data.get("language", "en")
        self.voice = data.get("voice", "en_US-libritts_r-medium")
        self.level = data.get("level", "medium")
        
        # Enhanced conversation memory
        self.conversation_context = data.get("conversation_context", [])
        self.session_start_time = data.get("session_start_time", time.time())
        self.last_interaction_time = data.get("last_interaction_time", time.time())
        self.total_interactions = data.get("total_interactions", 0)
        self.conversation_topics = data.get("conversation_topics", [])
        self.user_preferences = data.get("user_preferences", {})
        
        # Role play data
        self.role_play_enabled = data.get("role_play_enabled", False)
        self.role_play_template = data.get("role_play_template", "school")
        self.organization_name = data.get("organization_name", "")
        self.organization_details = data.get("organization_details", "")
        self.role_title = data.get("role_title", "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary with enhanced conversation context"""
        return {
            "user_name": self.user_name,
            "last_destination": self.last_destination,
            "facts": self.facts,
            "traits": self.traits,
            "history": self.history,
            "greeted": self.greeted,
            "language": self.language,
            "voice": self.voice,
            "level": self.level,
            "conversation_context": self.conversation_context,
            "session_start_time": self.session_start_time,
            "last_interaction_time": self.last_interaction_time,
            "total_interactions": self.total_interactions,
            "conversation_topics": self.conversation_topics,
            "user_preferences": self.user_preferences,
            "role_play_enabled": self.role_play_enabled,
            "role_play_template": self.role_play_template,
            "organization_name": self.organization_name,
            "organization_details": self.organization_details,
            "role_title": self.role_title
        }

    def load_role_play_from_db(self, client_id: str):
        """Load role play configuration from database"""
        try:
            conn = sqlite3.connect(settings.DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT role_play_enabled, role_play_template, organization_name, 
                       organization_details, role_title
                FROM role_play_configs 
                WHERE client_id = ?
            """, (client_id,))
            
            result = cursor.fetchone()
            if result:
                self.role_play_enabled = bool(result[0])
                self.role_play_template = result[1] or "school"
                self.organization_name = result[2] or ""
                self.organization_details = result[3] or ""
                self.role_title = result[4] or ""
                
            conn.close()
        except Exception as e:
            log.error(f"Error loading role play config: {e}")


class MemoryStore:
    """Persistent memory storage"""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.db_path = settings.DB_PATH

    def save(self, memory: SessionMemory):
        """Save memory to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_memories (
                    client_id TEXT PRIMARY KEY,
                    memory_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Save memory data
            memory_data = json.dumps(memory.to_dict())
            cursor.execute("""
                INSERT OR REPLACE INTO user_memories (client_id, memory_data)
                VALUES (?, ?)
            """, (self.client_id, memory_data))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            log.error(f"Error saving memory: {e}")

    def load(self) -> Optional[Dict[str, Any]]:
        """Load memory from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT memory_data FROM user_memories WHERE client_id = ?
            """, (self.client_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            return None
            
        except Exception as e:
            log.error(f"Error loading memory: {e}")
            return None

