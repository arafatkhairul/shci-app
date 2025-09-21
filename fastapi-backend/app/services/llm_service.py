"""
LLM Service for AI interactions
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, AsyncGenerator
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
                log.info(f"🔄 LLM request attempt {attempt + 1}/{self.retries} to {self.api_url}")
                timeout_config = aiohttp.ClientTimeout(total=self.timeout, connect=10.0)
                async with aiohttp.ClientSession(timeout=timeout_config) as session:
                    async with session.post(self.api_url, json=payload, headers=headers) as response:
                        log.info(f"📡 LLM API response status: {response.status}")
                        if response.status == 200:
                            data = await response.json()
                            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                            log.info(f"✅ LLM response received: {len(content)} characters")
                            return content
                        else:
                            error_text = await response.text()
                            log.warning(f"⚠️ LLM API returned status {response.status}: {error_text}")
                            
            except asyncio.TimeoutError:
                log.warning(f"⏰ LLM request timeout after {self.timeout}s (attempt {attempt + 1}/{self.retries})")
            except aiohttp.ClientError as e:
                log.warning(f"🌐 LLM connection error (attempt {attempt + 1}/{self.retries}): {str(e)}")
            except Exception as e:
                log_exception(log, f"❌ LLM request error (attempt {attempt + 1}/{self.retries})", e)
                
            if attempt < self.retries - 1:
                wait_time = (attempt + 1) * 2  # Exponential backoff
                log.info(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
        
        return None

    async def generate_streaming_response(
        self, 
        messages: list, 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """Generate streaming response from LLM"""
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        try:
            log.info(f"🔄 LLM streaming request to {self.api_url}")
            timeout_config = aiohttp.ClientTimeout(total=self.timeout, connect=10.0)
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    log.info(f"📡 LLM streaming API response status: {response.status}")
                    if response.status == 200:
                        chunk_count = 0
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data_str = line[6:]  # Remove 'data: ' prefix
                                if data_str == '[DONE]':
                                    log.info(f"✅ LLM streaming completed with {chunk_count} chunks")
                                    break
                                try:
                                    data = json.loads(data_str)
                                    if 'choices' in data and len(data['choices']) > 0:
                                        delta = data['choices'][0].get('delta', {})
                                        if 'content' in delta:
                                            chunk_count += 1
                                            yield delta['content']
                                except json.JSONDecodeError as e:
                                    log.debug(f"JSON decode error in streaming: {e}")
                                    continue
                    else:
                        error_text = await response.text()
                        log.warning(f"⚠️ LLM streaming API returned status {response.status}: {error_text}")
                        
        except asyncio.TimeoutError:
            log.warning(f"⏰ LLM streaming timeout after {self.timeout}s")
        except aiohttp.ClientError as e:
            log.warning(f"🌐 LLM streaming connection error: {str(e)}")
        except Exception as e:
            log_exception(log, "❌ LLM streaming error", e)

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

