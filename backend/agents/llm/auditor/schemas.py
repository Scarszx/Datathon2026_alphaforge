"""Sortie structurée de agent-auditor (règles déclenchées seulement)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuditItem(BaseModel):
    key: str = Field(description="The verdict group key exactly as received, for example R2:fail.")
    passage_refs: list[str] = Field(default_factory=list, description="Refs (P1, P2...) of the candidate passages of this group that state the principle the rule is inspired by; empty if none does.")
    message_en: str = Field(description="One English sentence saying which rule was triggered and why, without figures and without approval wording.")


class AuditReport(BaseModel):
    items: list[AuditItem] = Field(description="One item per verdict group received.")
