from __future__ import annotations

from app.contracts.health import HealthReport
from app.kernel.registry import ModuleRegistry


class HealthMonitor:
    def collect(self, registry: ModuleRegistry) -> dict[str, object]:
        module_reports: list[dict[str, object]] = []
        provider_reports: list[dict[str, object]] = []

        for module in registry.list_modules():
            try:
                report = module.health_check()
            except Exception as exc:
                report = HealthReport(
                    component_id=module.manifest.module_id,
                    status="unhealthy",
                    summary=f"health_check exception: {exc}",
                )
            module_reports.append(report.to_dict())

        for provider in registry.list_providers():
            try:
                report = provider.health_check()
            except Exception as exc:
                report = HealthReport(
                    component_id=provider.provider_id,
                    status="unhealthy",
                    summary=f"health_check exception: {exc}",
                )
            provider_reports.append(report.to_dict())

        all_ok = all(bool(item.get("ok")) for item in [*module_reports, *provider_reports]) if (module_reports or provider_reports) else True
        return {
            "ok": all_ok,
            "modules": module_reports,
            "providers": provider_reports,
        }
