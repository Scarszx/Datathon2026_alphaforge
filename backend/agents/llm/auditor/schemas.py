"""Sortie structurée de agent-auditor."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuditItem(BaseModel):
    key: str = Field(description="The verdict group key exactly as received, for example R2:fail.")
    passage_refs: list[str] = Field(default_factory=list, description="Refs (P1, P2...) of the candidate passages of this group that state the rule's regulatory principle; empty if none does.")
    message_en: str = Field(description="One English sentence explaining the verdict, without figures.")


class AuditReport(BaseModel):
    items: list[AuditItem] = Field(description="One item per verdict group received.")
