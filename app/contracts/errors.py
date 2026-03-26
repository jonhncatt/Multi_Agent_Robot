from __future__ import annotations


class AgentOSError(RuntimeError):
    """Base error for Agent OS runtime."""


class CompatibilityError(AgentOSError):
    """Raised when manifest compatibility check fails."""


class ModuleLoadError(AgentOSError):
    """Raised when module loader cannot load module entrypoint."""


class ModuleInitError(AgentOSError):
    """Raised when module init fails."""


class ProviderUnavailableError(AgentOSError):
    """Raised when no provider can serve a tool call."""


class ToolExecutionError(AgentOSError):
    """Raised when tool execution fails after retries/fallback."""
