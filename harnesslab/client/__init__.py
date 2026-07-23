"""Chat clients: OpenAI-compatible live (vLLM/Blablador) and deterministic mock."""

from .base import ChatClient, ChatResult, ClientError  # noqa: F401
from .mock import MockClient, scripted  # noqa: F401
from .multi import MultiEndpointClient  # noqa: F401
from .openai_compat import OpenAICompatClient  # noqa: F401
