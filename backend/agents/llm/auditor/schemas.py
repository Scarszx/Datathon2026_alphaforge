"""Sortie structurée de agent-auditor."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuditItem(BaseModel):
    key: str = Field(description="The verdict group key exactly as received, for example R2:fail.")
    passage_refs: list[str] = Field(default_factory=list, description="Refs of supporting passages returned by search_regulation (P1, P2...); empty if none supports the verdict.")
    message_en: str = Field(description="One English sentence explaining the verdict, without figures.")


class AuditReport(BaseModel):
    items: list[AuditItem] = Field(description="One item per verdict group received.")
