"""
LLM Service for AI interactions
"""
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from app.config.settings import settings
from app.utils.logger import get_logger, log_exception

log = get_logger("llm_service")

class LLMService:
    """Service for interacting with Large Language Models"""
    
    def __init__(self):
        self.api_url = settings.LLM_API_URL
        self.model = settings.LLM_MODEL
        self.api_key = settings.LLM_API_KEY
        self.timeout = settings.LLM_TIMEOUT
        self.retries = settings.LLM_RETRIES

    async def generate_response(
        self, 
        messages: list, 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """Generate response from LLM"""
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(self.api_url, json=payload, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        else:
                            log.warning(f"LLM API returned status {response.status}")
                            
            except asyncio.TimeoutError:
                log.warning(f"LLM request timeout (attempt {attempt + 1}/{self.retries})")
            except Exception as e:
                log_exception(log, f"LLM request error (attempt {attempt + 1}/{self.retries})", e)
                
            if attempt < self.retries - 1:
                await asyncio.sleep(1)  # Wait before retry
        
        return None

    async def generate_with_context(
        self,
        user_message: str,
        context: list,
        persona: str,
        language: str = "en"
    ) -> Optional[str]:
        """Generate response with conversation context"""
        
        messages = [
            {"role": "system", "content": persona}
        ]
        
        # Add conversation context
        messages.extend(context)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return await self.generate_response(messages)

    def create_context_messages(self, history: list, max_turns: int = 5) -> list:
        """Create context messages from conversation history"""
        recent_history = history[-max_turns:] if len(history) > max_turns else history
        
        context_messages = []
        for entry in recent_history:
            context_messages.append({
                "role": entry["role"],
                "content": entry["content"]
            })
        
        return context_messages

