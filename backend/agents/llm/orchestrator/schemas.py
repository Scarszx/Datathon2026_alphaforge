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


class TranslationEdit(BaseModel):
    item: int = Field(description="The 'item' number of the flagged translation to correct.")
    find: str = Field(description="Exact text to find in that translation (a short span, copied character for character).")
    replace: str = Field(description="Text that replaces the first occurrence of `find`.")


class TranslationFixes(BaseModel):
    fixes: list[TranslationEdit] = Field(
        default_factory=list,
        description="Only the corrections, as find/replace pairs. Empty if no flagged translation can be fixed with a local edit.",
    )


class Refusal(BaseModel):
    reply: str = Field(description="The short explained refusal, in the requested language, ending with one simulation the user can ask for.")
