"""Comandos canônicos incrementais do V2."""

from __future__ import annotations

from typing import Literal

from app.v2.contracts.envelopes import CommandEnvelope


class CreateTechnicalCaseCommandV1(CommandEnvelope):
    contract_name: Literal["CreateTechnicalCaseCommandV1"] = "CreateTechnicalCaseCommandV1"


__all__ = [
    "CommandEnvelope",
    "CreateTechnicalCaseCommandV1",
]
