"""Sortie structurée de agent-writer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SectionText(BaseModel):
    """Sortie d'un appel du rédacteur : une seule section (celle demandée dans le prompt)."""

    text: str = Field(description="The requested section, with placeholders only and no figure.")
