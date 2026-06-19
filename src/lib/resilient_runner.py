import asyncio
import logging

from openai import APIConnectionError, InternalServerError, RateLimitError

from src.lib.openrouter_runner import OpenRouterAgent, OpenRouterResponse

logger = logging.getLogger(__name__)

class ResilientOpenRouterAgent(OpenRouterAgent):
    """An OpenRouterAgent that automatically retries on rate limits and server errors."""

    def __init__(self, *args, max_retries: int = 3, base_delay: float = 2.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def chat(self, prompt: str) -> OpenRouterResponse:
        original_create = self.client.chat.completions.create

        async def _retrying_create(*args, **kwargs):
            last_err = None
            for attempt in range(self.max_retries + 1):
                try:
                    return await original_create(*args, **kwargs)
                except (RateLimitError, APIConnectionError, InternalServerError) as e:
                    last_err = e
                    if attempt == self.max_retries:
                        break
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"OpenAI API error ({type(e).__name__}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
            if last_err:
                raise last_err

        # Patch the client's create method for this chat call
        self.client.chat.completions.create = _retrying_create
        try:
            return await super().chat(prompt)
        finally:
            self.client.chat.completions.create = original_create
