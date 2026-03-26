from __future__ import annotations

from app.contracts.errors import CompatibilityError
from app.contracts.manifest import ModuleManifest


def _parse_version(raw: str) -> tuple[int, ...]:
    parts: list[int] = []
    for token in str(raw or "").strip().split("."):
        token = token.strip()
        if not token:
            continue
        try:
            parts.append(int(token))
        except Exception:
            parts.append(0)
    return tuple(parts or [0])


class CompatibilityChecker:
    def __init__(self, *, kernel_version: str) -> None:
        self.kernel_version = str(kernel_version or "1.0.0").strip() or "1.0.0"

    def assert_manifest_compatible(self, manifest: ModuleManifest) -> None:
        if _parse_version(self.kernel_version) < _parse_version(manifest.min_kernel_version):
            raise CompatibilityError(
                f"module {manifest.identity()} requires kernel>={manifest.min_kernel_version}, got {self.kernel_version}"
            )
