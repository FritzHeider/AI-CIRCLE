"""AdapterRegistry — singleton that maps adapter_type strings to AgentAdapter instances."""
from __future__ import annotations

import logging
from typing import Dict, Optional, Type

from adapters.base import AgentAdapter

logger = logging.getLogger(__name__)

_REGISTRY: Dict[str, AgentAdapter] = {}


def register_adapter(adapter_type: str):
    """
    Class decorator that registers an AgentAdapter subclass.

    Usage::

        @register_adapter("claude")
        class ClaudeAdapter(AgentAdapter):
            ...
    """
    def decorator(cls: Type[AgentAdapter]) -> Type[AgentAdapter]:
        instance = cls()
        _REGISTRY[adapter_type] = instance
        logger.debug("Registered adapter: %s → %s", adapter_type, cls.__name__)
        return cls
    return decorator


class AdapterRegistry:
    """Provides access to registered adapters."""

    _instance: Optional["AdapterRegistry"] = None

    def __init__(self) -> None:
        # Ensure all adapters are imported so their decorators fire
        self._ensure_imports()

    @classmethod
    def instance(cls) -> "AdapterRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def _ensure_imports() -> None:
        """Import all adapter modules to trigger registration."""
        try:
            import adapters.human_adapter  # noqa: F401
        except Exception as e:
            logger.warning("Failed to import human_adapter: %s", e)
        try:
            import adapters.claude_adapter  # noqa: F401
        except Exception as e:
            logger.warning("Failed to import claude_adapter: %s", e)
        try:
            import adapters.openai_adapter  # noqa: F401
        except Exception as e:
            logger.warning("Failed to import openai_adapter: %s", e)
        try:
            import adapters.gemini_adapter  # noqa: F401
        except Exception as e:
            logger.warning("Failed to import gemini_adapter: %s", e)
        try:
            import adapters.falai_adapter  # noqa: F401
        except Exception as e:
            logger.warning("Failed to import falai_adapter: %s", e)

    def get(self, adapter_type: str) -> Optional[AgentAdapter]:
        adapter = _REGISTRY.get(adapter_type)
        if adapter is None:
            logger.warning("No adapter registered for type: %s", adapter_type)
        return adapter

    def list_types(self) -> list[str]:
        return list(_REGISTRY.keys())
