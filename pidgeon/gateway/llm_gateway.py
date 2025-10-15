"""LLM Gateway for provider abstraction and unified interface."""

import asyncio
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import hashlib

import openai
from anthropic import AsyncAnthropic
import orjson

from pidgeon.core.config import Config

logger = logging.getLogger(__name__)


class LLMResponse:
    """Response from LLM provider."""
    
    def __init__(
        self,
        content: str,
        model: str,
        provider: str,
        tokens_used: int = 0,
        finish_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.model = model
        self.provider = provider
        self.tokens_used = tokens_used
        self.finish_reason = finish_reason
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()


class LLMGateway:
    """Unified gateway for multiple LLM providers.
    
    Provides:
    - Provider abstraction (OpenAI, Anthropic, etc.)
    - Automatic retry with exponential backoff
    - Response caching
    - Usage and cost tracking
    """
    
    def __init__(self, config: Config, redis_client: Optional[Any] = None):
        """Initialize LLM Gateway.
        
        Args:
            config: Configuration object
            redis_client: Optional Redis client for caching
        """
        self.config = config
        self.redis = redis_client
        
        # Initialize providers
        self._openai_client: Optional[openai.AsyncOpenAI] = None
        self._anthropic_client: Optional[AsyncAnthropic] = None
        
        # Usage tracking
        self.total_tokens = 0
        self.request_count = 0
        
        # Cache settings
        self.cache_enabled = config.get('llm.cache_enabled', True)
        self.cache_ttl = config.get('llm.cache_ttl_seconds', 3600)
    
    def _get_openai_client(self) -> openai.AsyncOpenAI:
        """Get or create OpenAI client."""
        if self._openai_client is None:
            api_key = self.config.get('llm.providers.openai.api_key')
            if not api_key:
                raise ValueError("OpenAI API key not configured")
            self._openai_client = openai.AsyncOpenAI(api_key=api_key)
        return self._openai_client
    
    def _get_anthropic_client(self) -> AsyncAnthropic:
        """Get or create Anthropic client."""
        if self._anthropic_client is None:
            api_key = self.config.get('llm.providers.anthropic.api_key')
            if not api_key:
                raise ValueError("Anthropic API key not configured")
            self._anthropic_client = AsyncAnthropic(api_key=api_key)
        return self._anthropic_client
    
    def _get_cache_key(self, prompt: str, model: str, **kwargs) -> str:
        """Generate cache key for request."""
        key_data = {
            'prompt': prompt,
            'model': model,
            **{k: v for k, v in kwargs.items() if k in ['temperature', 'max_tokens']}
        }
        key_str = orjson.dumps(key_data, option=orjson.OPT_SORT_KEYS).decode()
        return f"pidgeon:llm:cache:{hashlib.sha256(key_str.encode()).hexdigest()}"
    
    async def _get_cached_response(self, cache_key: str) -> Optional[LLMResponse]:
        """Get cached response if available."""
        if not self.cache_enabled or self.redis is None:
            return None
        
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                data = orjson.loads(cached)
                logger.debug(f"Cache hit for {cache_key}")
                return LLMResponse(**data)
        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
        
        return None
    
    async def _cache_response(self, cache_key: str, response: LLMResponse) -> None:
        """Cache LLM response."""
        if not self.cache_enabled or self.redis is None:
            return
        
        try:
            data = {
                'content': response.content,
                'model': response.model,
                'provider': response.provider,
                'tokens_used': response.tokens_used,
                'finish_reason': response.finish_reason,
                'metadata': response.metadata
            }
            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                orjson.dumps(data)
            )
            logger.debug(f"Cached response for {cache_key}")
        except Exception as e:
            logger.warning(f"Error caching response: {e}")
    
    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Send completion request to LLM provider.
        
        Args:
            prompt: User prompt/message
            model: Model name (uses default from config if not specified)
            provider: Provider name (openai, anthropic)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            system: System message/prompt
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse object
        """
        # Determine provider and model
        if provider is None:
            provider = self.config.llm_default_provider
        
        if model is None:
            model = self.config.get(f'llm.providers.{provider}.model')
        
        if temperature is None:
            temperature = self.config.get(f'llm.providers.{provider}.temperature', 0.7)
        
        if max_tokens is None:
            max_tokens = self.config.get(f'llm.providers.{provider}.max_tokens', 2000)
        
        # Check cache
        cache_key = self._get_cache_key(prompt, model, temperature=temperature, max_tokens=max_tokens)
        cached = await self._get_cached_response(cache_key)
        if cached:
            return cached
        
        # Route to provider with retry
        response = await self._complete_with_retry(
            provider, prompt, model, temperature, max_tokens, system, **kwargs
        )
        
        # Cache response
        await self._cache_response(cache_key, response)
        
        # Track usage
        self.total_tokens += response.tokens_used
        self.request_count += 1
        
        return response
    
    async def _complete_with_retry(
        self,
        provider: str,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        system: Optional[str],
        max_retries: int = 3,
        **kwargs
    ) -> LLMResponse:
        """Complete with exponential backoff retry."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if provider == "openai":
                    return await self._complete_openai(prompt, model, temperature, max_tokens, system, **kwargs)
                elif provider == "anthropic":
                    return await self._complete_anthropic(prompt, model, temperature, max_tokens, system, **kwargs)
                else:
                    raise ValueError(f"Unknown provider: {provider}")
                    
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"LLM request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"LLM request failed after {max_retries} attempts: {e}")
        
        raise last_error
    
    async def _complete_openai(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        system: Optional[str],
        **kwargs
    ) -> LLMResponse:
        """Complete using OpenAI API."""
        client = self._get_openai_client()
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=model,
            provider="openai",
            tokens_used=response.usage.total_tokens if response.usage else 0,
            finish_reason=response.choices[0].finish_reason,
            metadata={'response_id': response.id}
        )
    
    async def _complete_anthropic(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        system: Optional[str],
        **kwargs
    ) -> LLMResponse:
        """Complete using Anthropic API."""
        client = self._get_anthropic_client()
        
        message_kwargs = {
            'model': model,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'messages': [{"role": "user", "content": prompt}],
            **kwargs
        }
        
        if system:
            message_kwargs['system'] = system
        
        response = await client.messages.create(**message_kwargs)
        
        # Extract text content
        content = ""
        if response.content:
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text
        
        return LLMResponse(
            content=content,
            model=model,
            provider="anthropic",
            tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else 0,
            finish_reason=response.stop_reason,
            metadata={'response_id': response.id}
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            'total_tokens': self.total_tokens,
            'request_count': self.request_count,
            'avg_tokens_per_request': self.total_tokens / self.request_count if self.request_count > 0 else 0
        }


