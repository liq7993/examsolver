"""LLM abstraction layer for cloud and local model clients."""

from examsolver.llm.base import LLMClient, Message
from examsolver.llm.claude_client import ClaudeClient
from examsolver.llm.local_gguf import LocalGGUFClient
from examsolver.llm.router import pick_llm

__all__ = ["ClaudeClient", "LLMClient", "LocalGGUFClient", "Message", "pick_llm"]
