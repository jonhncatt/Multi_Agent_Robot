from __future__ import annotations


class WorkerRole:
    role_id = "worker"

    def describe(self) -> str:
        return "Execute tools and produce task output."
