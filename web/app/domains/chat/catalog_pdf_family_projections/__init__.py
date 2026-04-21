from __future__ import annotations

from typing import Any

from .nr01 import apply_nr01_projection
from .nr04 import apply_nr04_projection
from .nr05 import apply_nr05_projection
from .nr06 import apply_nr06_projection
from .nr07 import apply_nr07_projection
from .nr08 import apply_nr08_projection
from .nr09 import apply_nr09_projection
from .nr11 import apply_nr11_projection
from .nr14 import apply_nr14_projection
from .nr15 import apply_nr15_projection
from .nr16 import apply_nr16_projection
from .nr17 import apply_nr17_projection
from .nr19 import apply_nr19_projection
from .nr21 import apply_nr21_projection
from .nr23 import apply_nr23_projection
from .nr24 import apply_nr24_projection
from .nr25 import apply_nr25_projection
from .nr26 import apply_nr26_projection
from .nr20 import apply_nr20_projection
from .nr22 import apply_nr22_projection
from .nr29 import apply_nr29_projection
from .nr30 import apply_nr30_projection
from .nr31 import apply_nr31_projection
from .nr32 import apply_nr32_projection
from .nr33 import apply_nr33_projection
from .nr34 import apply_nr34_projection
from .nr36 import apply_nr36_projection
from .nr37 import apply_nr37_projection
from .nr38 import apply_nr38_projection
from .nr10 import (
    apply_nr10_loto_projection,
    apply_nr10_projection,
    apply_nr10_prontuario_projection,
    apply_nr10_spda_projection,
)
from .nr12 import apply_nr12_projection, apply_nr12_risk_projection
from .nr13 import apply_nr13_projection
from .nr18 import apply_nr18_projection
from .nr35 import apply_nr35_projection


def apply_catalog_family_projections(
    *,
    payload: dict[str, Any],
    existing_payload: dict[str, Any] | None,
    family_key: str,
    laudo: Any,
    location_hint: str | None,
    summary_hint: str | None,
    recommendation_hint: str | None,
    title_hint: str | None,
) -> None:
    shared_kwargs = {
        "payload": payload,
        "existing_payload": existing_payload,
        "family_key": family_key,
        "laudo": laudo,
        "location_hint": location_hint,
        "summary_hint": summary_hint,
        "recommendation_hint": recommendation_hint,
        "title_hint": title_hint,
    }
    apply_nr01_projection(**shared_kwargs)
    apply_nr04_projection(**shared_kwargs)
    apply_nr05_projection(**shared_kwargs)
    apply_nr06_projection(**shared_kwargs)
    apply_nr07_projection(**shared_kwargs)
    apply_nr08_projection(**shared_kwargs)
    apply_nr09_projection(**shared_kwargs)
    apply_nr11_projection(**shared_kwargs)
    apply_nr14_projection(**shared_kwargs)
    apply_nr15_projection(**shared_kwargs)
    apply_nr16_projection(**shared_kwargs)
    apply_nr17_projection(**shared_kwargs)
    apply_nr19_projection(**shared_kwargs)
    apply_nr21_projection(**shared_kwargs)
    apply_nr23_projection(**shared_kwargs)
    apply_nr24_projection(**shared_kwargs)
    apply_nr25_projection(**shared_kwargs)
    apply_nr26_projection(**shared_kwargs)
    apply_nr13_projection(**shared_kwargs)
    apply_nr10_projection(**shared_kwargs)
    apply_nr10_loto_projection(**shared_kwargs)
    apply_nr10_prontuario_projection(**shared_kwargs)
    apply_nr10_spda_projection(**shared_kwargs)
    apply_nr12_projection(**shared_kwargs)
    apply_nr12_risk_projection(**shared_kwargs)
    apply_nr18_projection(**shared_kwargs)
    apply_nr20_projection(**shared_kwargs)
    apply_nr22_projection(**shared_kwargs)
    apply_nr29_projection(**shared_kwargs)
    apply_nr30_projection(**shared_kwargs)
    apply_nr31_projection(**shared_kwargs)
    apply_nr32_projection(**shared_kwargs)
    apply_nr33_projection(**shared_kwargs)
    apply_nr34_projection(**shared_kwargs)
    apply_nr36_projection(**shared_kwargs)
    apply_nr37_projection(**shared_kwargs)
    apply_nr38_projection(**shared_kwargs)
    apply_nr35_projection(**shared_kwargs)


__all__ = ["apply_catalog_family_projections"]
