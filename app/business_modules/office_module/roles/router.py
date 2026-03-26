from __future__ import annotations


class RouterRole:
    role_id = "router"

    def describe(self) -> str:
        return "Route task intent to minimal execution path."
