"""Sortie structurée de agent-writer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WriterSections(BaseModel):
    data_used: str = Field(description="Which data and methods produced the figures, with placeholders only.")
    why: str = Field(description="Why each scenario got its verdict, with placeholders only.")
    limits: str = Field(description="Limits and uncertainties, with placeholders only.")
    what_would_change: str = Field(description="Which mandate inputs would change the answer, with placeholders only.")
