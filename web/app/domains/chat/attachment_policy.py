"""Attachment policy helpers shared by inspector chat surfaces."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domains.chat.chat_runtime import MIME_DOC_PERMITIDOS
from app.domains.chat.limits_helpers import obter_limite_empresa
from app.shared.database import Usuario
from app.v2.contracts.mobile import MobileInspectorAttachmentPolicyV2

_IMAGE_MIME_TYPES = [
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
]


def build_mobile_attachment_policy_payload(
    *,
    usuario: Usuario,
    banco: Session,
) -> dict[str, object]:
    limite = obter_limite_empresa(usuario, banco)
    supports_document = bool(limite and getattr(limite, "upload_doc", False))
    supported_categories = ["imagem"]
    supported_mime_types = list(_IMAGE_MIME_TYPES)

    if supports_document:
        supported_categories.append("documento")
        supported_mime_types.extend(MIME_DOC_PERMITIDOS.keys())

    return MobileInspectorAttachmentPolicyV2(
        supported_categories=supported_categories,
        supported_mime_types=supported_mime_types,
    ).model_dump(mode="json")


__all__ = ["build_mobile_attachment_policy_payload"]
