from __future__ import annotations

"""Retired compatibility placeholder for the former office runtime shim.

The canonical office execution implementation now lives in
`packages.office_modules.office_agent_runtime.OfficeAgent`.
This module remains only as a temporary compatibility re-export while any
external references are being cleaned up.
"""

from packages.office_modules.office_agent_runtime import OfficeAgent

__all__ = ["OfficeAgent"]
