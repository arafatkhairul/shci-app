"""
Memory Management Endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from app.models.session_memory import MemoryStore
from app.utils.logger import get_logger

log = get_logger("memory_endpoints")
router = APIRouter()

@router.get("/conversation/{client_id}")
async def get_conversation_history(client_id: str, limit: int = 20):
    """Get conversation history for a specific client"""
    try:
        memory_store = MemoryStore(client_id)
        memory_data = memory_store.load()
        
        if not memory_data:
            return {
                "client_id": client_id,
                "conversation_context": [],
                "conversation_summary": {},
                "message": "No conversation history found"
            }
        
        # Create a temporary SessionMemory object to get enhanced context
        from app.models.session_memory import SessionMemory
        temp_memory = SessionMemory()
        temp_memory.load_from_dict(memory_data)
        
        # Get conversation context
        conversation_context = temp_memory.get_enhanced_context(max_turns=limit)
        conversation_summary = temp_memory.get_conversation_summary()
        
        return {
            "client_id": client_id,
            "conversation_context": conversation_context,
            "conversation_summary": conversation_summary,
            "total_interactions": len(conversation_context)
        }
        
    except Exception as e:
        log.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation history: {str(e)}")

@router.get("/conversation/{client_id}/summary")
async def get_conversation_summary(client_id: str):
    """Get conversation summary for a specific client"""
    try:
        memory_store = MemoryStore(client_id)
        memory_data = memory_store.load()
        
        if not memory_data:
            return {
                "client_id": client_id,
                "conversation_summary": {},
                "message": "No conversation history found"
            }
        
        # Create a temporary SessionMemory object
        from app.models.session_memory import SessionMemory
        temp_memory = SessionMemory()
        temp_memory.load_from_dict(memory_data)
        
        conversation_summary = temp_memory.get_conversation_summary()
        
        return {
            "client_id": client_id,
            "conversation_summary": conversation_summary
        }
        
    except Exception as e:
        log.error(f"Error getting conversation summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation summary: {str(e)}")

@router.delete("/conversation/{client_id}")
async def clear_conversation_history(client_id: str):
    """Clear conversation history for a specific client"""
    try:
        memory_store = MemoryStore(client_id)
        
        # Create empty memory
        from app.models.session_memory import SessionMemory
        empty_memory = SessionMemory()
        empty_memory.client_id = client_id
        
        # Save empty memory
        memory_store.save(empty_memory)
        
        return {
            "client_id": client_id,
            "message": "Conversation history cleared successfully"
        }
        
    except Exception as e:
        log.error(f"Error clearing conversation history: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing conversation history: {str(e)}")

@router.get("/conversation/{client_id}/topics")
async def get_conversation_topics(client_id: str):
    """Get topics discussed in conversation for a specific client"""
    try:
        memory_store = MemoryStore(client_id)
        memory_data = memory_store.load()
        
        if not memory_data:
            return {
                "client_id": client_id,
                "topics": [],
                "message": "No conversation history found"
            }
        
        # Create a temporary SessionMemory object
        from app.models.session_memory import SessionMemory
        temp_memory = SessionMemory()
        temp_memory.load_from_dict(memory_data)
        
        topics = temp_memory.conversation_topics
        
        return {
            "client_id": client_id,
            "topics": topics,
            "total_topics": len(topics)
        }
        
    except Exception as e:
        log.error(f"Error getting conversation topics: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation topics: {str(e)}")

@router.get("/conversation/{client_id}/context")
async def get_conversation_context_for_llm(client_id: str, max_length: int = 1000):
    """Get optimized conversation context for LLM"""
    try:
        memory_store = MemoryStore(client_id)
        memory_data = memory_store.load()
        
        if not memory_data:
            return {
                "client_id": client_id,
                "context": [],
                "message": "No conversation history found"
            }
        
        # Create a temporary SessionMemory object
        from app.models.session_memory import SessionMemory
        temp_memory = SessionMemory()
        temp_memory.load_from_dict(memory_data)
        
        context = temp_memory.get_context_for_llm(max_length=max_length)
        
        return {
            "client_id": client_id,
            "context": context,
            "context_length": len(context),
            "max_length": max_length
        }
        
    except Exception as e:
        log.error(f"Error getting conversation context: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation context: {str(e)}")

