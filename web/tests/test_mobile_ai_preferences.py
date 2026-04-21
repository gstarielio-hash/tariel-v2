from app.domains.chat.core_helpers import obter_preview_primeira_mensagem
from app.domains.chat.mobile_ai_preferences import (
    anexar_preferencias_ia_mobile_na_mensagem,
    extrair_preferencias_ia_mobile_embutidas,
    limpar_historico_visivel_chat,
    limpar_texto_visivel_chat,
)


def test_extrai_preferencias_embutidas_sem_poluir_texto_visivel() -> None:
    texto, preferencias = extrair_preferencias_ia_mobile_embutidas(
        "[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]\n\nVerifique a válvula."
    )

    assert texto == "Verifique a válvula."
    assert "use tom técnico" in preferencias


def test_anexa_preferencias_so_no_contexto_interno() -> None:
    mensagem = anexar_preferencias_ia_mobile_na_mensagem(
        "Registrar pressão do vaso.",
        preferencias_ia_mobile="[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]",
    )

    assert mensagem.startswith("[preferencias_ia_mobile]")
    assert mensagem.endswith("Registrar pressão do vaso.")


def test_limpa_historico_visivel_e_aplica_fallback_para_evidencia() -> None:
    historico = limpar_historico_visivel_chat(
        [
            {
                "papel": "usuario",
                "texto": "[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]",
            },
            {
                "papel": "assistente",
                "texto": "Resposta consolidada",
            },
        ]
    )

    assert historico == [
        {"papel": "usuario", "texto": "Evidência enviada"},
        {"papel": "assistente", "texto": "Resposta consolidada"},
    ]
    assert (
        limpar_texto_visivel_chat(
            "[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]",
            fallback_hidden_only="Evidência enviada",
        )
        == "Evidência enviada"
    )
    assert (
        obter_preview_primeira_mensagem(
            "[preferencias_ia_mobile]\nuse tom técnico\n[/preferencias_ia_mobile]"
        )
        == "Evidência enviada"
    )
