from __future__ import annotations


class ReviewerRole:
    role_id = "reviewer"

    def describe(self) -> str:
        return "Review evidence coverage and risk before final response."
