"""Model clients for API calls."""

import json
import os
from typing import Optional
from openai import OpenAI
from pydantic import BaseModel, Field

from sycop.config import ModelConfig, Settings


class GenerationMeta(BaseModel):
    """Metadata from generation."""
    model: str
    provider: str
    temperature: float
    max_tokens: int
    token_usage: Optional[dict] = None
    response_id: Optional[str] = None
    created: Optional[int] = None


class ModelClient:
    """Client for model API calls."""

    def __init__(self, config: ModelConfig, settings: Optional[Settings] = None):
        self.config = config
        self.settings = settings or Settings()
        
        if config.provider == "openai":
            api_key = self.settings.openai_api_key
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.client = OpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")

    def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> tuple[str, GenerationMeta]:
        """Generate a response from the model."""
        # Prepend system prompt if provided
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        if self.config.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=full_messages,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                max_tokens=self.config.max_tokens,
            )
            
            text = response.choices[0].message.content or ""
            
            meta = GenerationMeta(
                model=self.config.model,
                provider=self.config.provider,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                token_usage={
                    "input": response.usage.prompt_tokens,
                    "output": response.usage.completion_tokens,
                    "total": response.usage.total_tokens,
                } if response.usage else None,
                response_id=response.id,
                created=response.created,
            )
            
            return text, meta
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")

    def generate_json(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> tuple[dict, GenerationMeta]:
        """Generate a JSON response (for gate/correction strength)."""
        # Add JSON instruction to system prompt
        json_system = (system_prompt or "") + "\n\nReturn ONLY valid JSON. No markdown, no code blocks, just JSON."
        
        text, meta = self.generate(messages, json_system)
        
        # Try to extract JSON from response
        text = text.strip()
        if text.startswith("```"):
            # Remove code blocks
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        if text.startswith("```json"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        
        try:
            result = json.loads(text)
            return result, meta
        except json.JSONDecodeError:
            # Fallback: try to extract JSON object
            import re
            match = re.search(r'\{[^}]+\}', text)
            if match:
                try:
                    return json.loads(match.group()), meta
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to parse JSON from response: {text[:200]}")

