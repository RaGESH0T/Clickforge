"""Platform input backends used by the click engine."""

from __future__ import annotations

from clickforge.backends.base import (
    BackendUnavailable,
    InputBackend,
    InputBackendError,
)
from clickforge.backends.capabilities import BackendCapabilities


def create_backend(capabilities: BackendCapabilities) -> InputBackend:
    """Create the backend described by a capability probe."""
    if not capabilities.available:
        raise BackendUnavailable(
            capabilities.reason or "Synthetic input is unavailable on this session."
        )
    if capabilities.backend_id == "linux-x11-xtest":
        from clickforge.backends.x11 import X11InputBackend

        return X11InputBackend()
    if capabilities.backend_id == "windows-sendinput":
        from clickforge.backends.windows import WindowsInputBackend

        return WindowsInputBackend()
    raise BackendUnavailable(
        capabilities.reason or f"Unsupported input backend: {capabilities.backend_id}"
    )


__all__ = [
    "BackendUnavailable",
    "InputBackend",
    "InputBackendError",
    "create_backend",
]
