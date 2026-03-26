from __future__ import annotations


class RevisionRole:
    role_id = "revision"

    def describe(self) -> str:
        return "Apply final revision after review feedback."
