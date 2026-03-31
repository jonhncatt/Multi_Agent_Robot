"""API route namespace reserved for modular route registration."""

from app.api.routes.agents import router as agents_router
from app.api.routes.chat import router as chat_router

__all__ = ["agents_router", "chat_router"]
