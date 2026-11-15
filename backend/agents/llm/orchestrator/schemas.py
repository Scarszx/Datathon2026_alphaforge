"""Sorties structurées de agent-orchestrator (descriptions en anglais : le modèle les lit)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OrchestratorTurn(BaseModel):
    user_language: str = Field(description="ISO 639-1 code of the user's language, for example fr or en.")
    english_request: str = Field(description="Faithful English translation of the user's latest message.")
    reply: str = Field(description="Your answer to the user, in the user's language, with {EV-nn}/{KB-nn} placeholders unchanged.")
    quick_replies: list[str] = Field(
        default_factory=list, max_length=4,
        description="At most four short answers the user can click, in the user's language; empty if none.",
    )


class TranslationBatch(BaseModel):
    items: list[str] = Field(description="Translated items, same count and same order as received.")
