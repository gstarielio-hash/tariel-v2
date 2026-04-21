"""Bootstrap, seed e migração versionada da camada de persistência."""

from __future__ import annotations

import re
import time

from app.core.settings import env_bool, env_float, env_int, env_str
from app.domains.admin.mfa import generate_totp_secret
from sqlalchemy.exc import OperationalError


def _database_module():
    from app.shared import database as banco_dados

    return banco_dados


def _aplicar_migracoes_versionadas() -> None:
    try:
        from alembic import command
        from alembic.config import Config as AlembicConfig
    except (ModuleNotFoundError, ImportError) as erro:
        raise RuntimeError("Falha ao importar Alembic. Execute 'pip install -r requirements.txt' no .venv ativo.") from erro

    banco_dados = _database_module()
    if not banco_dados._ALEMBIC_INI.exists() or not banco_dados._ALEMBIC_DIR.exists():
        raise RuntimeError("Estrutura do Alembic não encontrada. Esperado: alembic.ini e pasta alembic/.")

    from sqlalchemy import inspect, text

    config = AlembicConfig(str(banco_dados._ALEMBIC_INI))
    config.set_main_option("script_location", banco_dados._ALEMBIC_DIR.as_posix())
    config.set_main_option("sqlalchemy.url", banco_dados.URL_BANCO)

    with banco_dados.motor_banco.begin() as conn:
        inspetor = inspect(conn)
        tabelas_existentes = set(inspetor.get_table_names())
        tabelas_esperadas = set(banco_dados.Base.metadata.tables.keys())
        sem_versionamento = "alembic_version" not in tabelas_existentes
        versao_vazia = False

        if not sem_versionamento:
            versao_vazia = conn.execute(text("SELECT COUNT(1) FROM alembic_version")).scalar_one() == 0

        tabelas_sem_versionamento = tabelas_existentes - {"alembic_version"}
        schema_legado_pronto = tabelas_esperadas.issubset(tabelas_sem_versionamento)

        config.attributes["connection"] = conn
        if schema_legado_pronto and (sem_versionamento or versao_vazia):
            banco_dados.logger.warning("Schema legado detectado sem versionamento Alembic. Aplicando stamp no head.")
            command.stamp(config, "head")
        else:
            command.upgrade(config, "head")


def _detectar_schema_incompleto() -> tuple[bool, list[str]]:
    from sqlalchemy import inspect

    banco_dados = _database_module()
    with banco_dados.motor_banco.connect() as conn:
        inspetor = inspect(conn)
        tabelas_existentes = set(inspetor.get_table_names())

    tabelas_esperadas = set(banco_dados.Base.metadata.tables.keys())
    tabelas_faltantes = sorted(tabelas_esperadas - tabelas_existentes)
    return bool(tabelas_faltantes), tabelas_faltantes


def _executar_bootstrap_banco_sem_retry() -> None:
    banco_dados = _database_module()
    run_migrations = env_bool(
        "DB_BOOTSTRAP_RUN_MIGRATIONS",
        not banco_dados._EM_PRODUCAO,
    )
    if run_migrations:
        _aplicar_migracoes_versionadas()
    else:
        schema_incompleto, tabelas_faltantes = _detectar_schema_incompleto()
        if schema_incompleto:
            banco_dados.logger.warning(
                "Schema do banco incompleto; executando migracoes versionadas automaticamente.",
                extra={
                    "db_bootstrap_run_migrations": False,
                    "db_missing_tables_count": len(tabelas_faltantes),
                    "db_missing_tables_sample": tabelas_faltantes[:10],
                },
            )
            _aplicar_migracoes_versionadas()
        else:
            banco_dados.logger.info(
                "Bootstrap do banco executando sem migracoes versionadas nesta inicializacao.",
                extra={"db_bootstrap_run_migrations": False},
            )
    seed_limites_plano()
    _bootstrap_admin_inicial_producao()
    _bootstrap_catalogo_canonico_producao()

    if not banco_dados._EM_PRODUCAO and banco_dados._SEED_DEV_BOOTSTRAP:
        _seed_dev()
    elif not banco_dados._EM_PRODUCAO:
        banco_dados.logger.info(
            "Seed DEV desabilitado (SEED_DEV_BOOTSTRAP=0). Nenhum usuário/senha de seed foi criado."
        )

    from sqlalchemy import text

    with banco_dados.motor_banco.connect() as conn:
        conn.execute(text("SELECT 1"))


def _descartar_pool_banco(banco_dados) -> None:
    dispose = getattr(getattr(banco_dados, "motor_banco", None), "dispose", None)
    if dispose is None:
        return

    try:
        dispose()
    except Exception:
        banco_dados.logger.warning(
            "Falha ao descartar o pool do banco apos erro operacional no bootstrap.",
            exc_info=True,
        )


def _executar_bootstrap_banco_com_retry() -> None:
    banco_dados = _database_module()
    max_attempts = max(env_int("DB_BOOTSTRAP_MAX_ATTEMPTS", 8), 1)
    retry_base_seconds = max(env_float("DB_BOOTSTRAP_RETRY_BASE_SECONDS", 2.0), 0.0)
    retry_max_seconds = max(env_float("DB_BOOTSTRAP_RETRY_MAX_SECONDS", 15.0), 0.0)

    for attempt in range(1, max_attempts + 1):
        try:
            _executar_bootstrap_banco_sem_retry()
            return
        except OperationalError:
            if attempt >= max_attempts:
                raise

            _descartar_pool_banco(banco_dados)
            wait_seconds = min(retry_max_seconds, retry_base_seconds * attempt) if retry_base_seconds > 0 else 0.0
            banco_dados.logger.warning(
                "Falha operacional ao inicializar o banco. Tentando novamente.",
                extra={
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "retry_in_seconds": wait_seconds,
                },
                exc_info=True,
            )
            if wait_seconds > 0:
                time.sleep(wait_seconds)


def inicializar_banco() -> None:
    banco_dados = _database_module()
    try:
        _executar_bootstrap_banco_com_retry()

        banco_dados.logger.info("Banco de dados inicializado com sucesso.")
    except Exception:
        banco_dados.logger.critical("Falha ao inicializar o banco.", exc_info=True)
        raise


def _seed_dev() -> None:
    from sqlalchemy import select

    from app.shared.security import criar_hash_senha

    banco_dados = _database_module()
    senha_padrao_seed = env_str("SEED_DEV_SENHA_PADRAO", "Dev@123456")
    senha_admin = env_str("SEED_ADMIN_SENHA", senha_padrao_seed)
    senha_admin_cliente = env_str("SEED_CLIENTE_SENHA", senha_padrao_seed)
    senha_inspetor = env_str("SEED_INSPETOR_SENHA", senha_padrao_seed)
    senha_revisor = env_str("SEED_REVISOR_SENHA", senha_padrao_seed)

    if senha_padrao_seed == "Dev@123456":
        banco_dados.logger.warning("Seed DEV usando senha padrão compartilhada. Não use isso fora de desenvolvimento.")

    with banco_dados.SessaoLocal() as banco:
        empresa = banco.scalar(select(banco_dados.Empresa).where(banco_dados.Empresa.cnpj == "00000000000000"))
        if not empresa:
            empresa = banco_dados.Empresa(
                nome_fantasia="Empresa Demo (DEV)",
                cnpj="00000000000000",
                plano_ativo=banco_dados.PlanoEmpresa.ILIMITADO.value,
            )
            banco.add(empresa)
            banco.flush()

        empresa_admin = _garantir_empresa_plataforma(
            banco,
            nome_empresa="Tariel.ia Interno (DEV)",
            cnpj_empresa="99999999999999",
        )

        usuarios_seed = [
            (
                empresa_admin.id,
                "admin@tariel.ia",
                "Diretoria Dev",
                int(banco_dados.NivelAcesso.DIRETORIA),
                senha_admin,
            ),
            (
                empresa.id,
                "admin-cliente@tariel.ia",
                "Admin-Cliente Dev",
                int(banco_dados.NivelAcesso.ADMIN_CLIENTE),
                senha_admin_cliente,
            ),
            (
                empresa.id,
                "inspetor@tariel.ia",
                "Inspetor Dev",
                int(banco_dados.NivelAcesso.INSPETOR),
                senha_inspetor,
            ),
            (
                empresa.id,
                "revisor@tariel.ia",
                "Engenheiro Revisor (Dev)",
                int(banco_dados.NivelAcesso.REVISOR),
                senha_revisor,
            ),
        ]

        for empresa_destino_id, email, nome, nivel, senha in usuarios_seed:
            usuario = banco.scalar(select(banco_dados.Usuario).where(banco_dados.Usuario.email == email))
            if usuario:
                usuario.empresa_id = empresa_destino_id
                usuario.nome_completo = nome
                usuario.nivel_acesso = nivel
                usuario.senha_hash = criar_hash_senha(senha)
                usuario.ativo = True
                usuario.tentativas_login = 0
                usuario.bloqueado_ate = None
                if nivel == int(banco_dados.NivelAcesso.DIRETORIA):
                    usuario.account_scope = "platform"
                    usuario.account_status = "active"
                    usuario.allowed_portals_json = ["admin"]
                    usuario.platform_role = "PLATFORM_OWNER"
                    usuario.mfa_required = True
                    usuario.mfa_secret_b32 = usuario.mfa_secret_b32 or generate_totp_secret()
                    usuario.can_password_login = True
                    usuario.can_google_login = True
                    usuario.can_microsoft_login = True
                    usuario.portal_admin_autorizado = True
                    usuario.admin_identity_status = "active"
                continue

            dados_usuario = {
                "empresa_id": empresa_destino_id,
                "nome_completo": nome,
                "email": email,
                "senha_hash": criar_hash_senha(senha),
                "nivel_acesso": nivel,
            }
            if nivel == int(banco_dados.NivelAcesso.DIRETORIA):
                dados_usuario["account_scope"] = "platform"
                dados_usuario["account_status"] = "active"
                dados_usuario["allowed_portals_json"] = ["admin"]
                dados_usuario["platform_role"] = "PLATFORM_OWNER"
                dados_usuario["mfa_required"] = True
                dados_usuario["mfa_secret_b32"] = generate_totp_secret()
                dados_usuario["can_password_login"] = True
                dados_usuario["can_google_login"] = True
                dados_usuario["can_microsoft_login"] = True
                dados_usuario["portal_admin_autorizado"] = True
                dados_usuario["admin_identity_status"] = "active"
            banco.add(banco_dados.Usuario(**dados_usuario))

        banco.commit()
        banco_dados.logger.info("Seed DEV garantido com sucesso.")


def _bootstrap_admin_inicial_producao() -> None:
    banco_dados = _database_module()
    if not banco_dados._EM_PRODUCAO:
        return

    email_admin = env_str("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    senha_admin = env_str("BOOTSTRAP_ADMIN_PASSWORD", "").strip()
    nome_admin = env_str("BOOTSTRAP_ADMIN_NOME", "Administrador Tariel.ia").strip() or "Administrador Tariel.ia"
    nome_empresa = (
        env_str("BOOTSTRAP_PLATFORM_EMPRESA_NOME", env_str("BOOTSTRAP_EMPRESA_NOME", "Tariel.ia Platform")).strip()
        or "Tariel.ia Platform"
    )
    cnpj_empresa = re.sub(
        r"\D+",
        "",
        env_str("BOOTSTRAP_PLATFORM_EMPRESA_CNPJ", env_str("BOOTSTRAP_EMPRESA_CNPJ", "99999999999999")),
    )

    if not email_admin or not senha_admin:
        banco_dados.logger.info(
            "Bootstrap inicial de produção ignorado: configure BOOTSTRAP_ADMIN_EMAIL e BOOTSTRAP_ADMIN_PASSWORD para criar o primeiro acesso."
        )
        return

    if len(cnpj_empresa) != 14:
        banco_dados.logger.warning("BOOTSTRAP_EMPRESA_CNPJ inválido. Usando placeholder 11111111111111.")
        cnpj_empresa = "11111111111111"

    from sqlalchemy import func, select

    from app.shared.security import criar_hash_senha

    with banco_dados.SessaoLocal() as banco:
        empresa = _garantir_empresa_plataforma(
            banco,
            nome_empresa=nome_empresa,
            cnpj_empresa=cnpj_empresa,
        )

        usuario = banco.scalar(select(banco_dados.Usuario).where(banco_dados.Usuario.email == email_admin))
        if usuario:
            usuario.empresa_id = int(empresa.id)
            usuario.nome_completo = nome_admin
            usuario.senha_hash = criar_hash_senha(senha_admin)
            usuario.nivel_acesso = int(banco_dados.NivelAcesso.DIRETORIA)
            usuario.ativo = True
            usuario.tentativas_login = 0
            usuario.bloqueado_ate = None
            usuario.status_bloqueio = False
            usuario.senha_temporaria_ativa = False
            usuario.account_scope = "platform"
            usuario.account_status = "active"
            usuario.allowed_portals_json = ["admin"]
            usuario.platform_role = "PLATFORM_OWNER"
            usuario.mfa_required = True
            usuario.mfa_secret_b32 = usuario.mfa_secret_b32 or generate_totp_secret()
            usuario.can_password_login = True
            usuario.can_google_login = True
            usuario.can_microsoft_login = True
            usuario.portal_admin_autorizado = True
            usuario.admin_identity_status = "active"
        else:
            total_usuarios = int(banco.scalar(select(func.count()).select_from(banco_dados.Usuario)) or 0)
            if total_usuarios > 0:
                banco_dados.logger.info(
                    "Bootstrap inicial de produção criando Admin-CEO %s mesmo com outros usuários já cadastrados.",
                    email_admin,
                )

            banco.add(
                banco_dados.Usuario(
                    empresa_id=int(empresa.id),
                    nome_completo=nome_admin,
                    email=email_admin,
                    senha_hash=criar_hash_senha(senha_admin),
                    nivel_acesso=int(banco_dados.NivelAcesso.DIRETORIA),
                    ativo=True,
                    senha_temporaria_ativa=False,
                    account_scope="platform",
                    account_status="active",
                    allowed_portals_json=["admin"],
                    platform_role="PLATFORM_OWNER",
                    mfa_required=True,
                    mfa_secret_b32=generate_totp_secret(),
                    can_password_login=True,
                    can_google_login=True,
                    can_microsoft_login=True,
                    portal_admin_autorizado=True,
                    admin_identity_status="active",
                )
            )
        banco.commit()
        banco_dados.logger.info("Bootstrap inicial de produção concluído para %s.", email_admin)


def _bootstrap_catalogo_canonico_producao() -> None:
    banco_dados = _database_module()
    if not banco_dados._EM_PRODUCAO:
        return
    if not env_bool("BOOTSTRAP_CATALOGO_CANONICO", True):
        banco_dados.logger.info(
            "Bootstrap canônico do catálogo ignorado: BOOTSTRAP_CATALOGO_CANONICO=0."
        )
        return

    from sqlalchemy import select

    from app.domains.admin.services import (
        importar_familias_canonicas_para_catalogo,
        listar_family_schemas_canonicos,
    )

    schemas = listar_family_schemas_canonicos()
    family_keys_canonicas: list[str] = []
    vistos: set[str] = set()
    for item in schemas:
        if str(item.get("catalog_classification") or "family").strip().lower() != "family":
            continue
        family_key = str(item.get("family_key") or "").strip().lower()
        if not family_key or family_key in vistos:
            continue
        vistos.add(family_key)
        family_keys_canonicas.append(family_key)

    if not family_keys_canonicas:
        banco_dados.logger.warning(
            "Bootstrap canônico do catálogo ignorado: nenhum family schema canônico foi encontrado."
        )
        return

    with banco_dados.SessaoLocal() as banco:
        family_keys_existentes = {
            str(item).strip().lower()
            for item in banco.scalars(
                select(banco_dados.FamiliaLaudoCatalogo.family_key).where(
                    banco_dados.FamiliaLaudoCatalogo.catalog_classification == "family"
                )
            ).all()
            if str(item).strip()
        }
        faltantes = [item for item in family_keys_canonicas if item not in family_keys_existentes]
        if not faltantes:
            banco_dados.logger.info(
                "Bootstrap canônico do catálogo já sincronizado. %s famílias presentes.",
                len(family_keys_existentes),
            )
            return

        admin_owner_id = banco.scalar(
            select(banco_dados.Usuario.id)
            .where(
                banco_dados.Usuario.portal_admin_autorizado.is_(True),
                banco_dados.Usuario.account_scope == "platform",
            )
            .order_by(banco_dados.Usuario.id.asc())
            .limit(1)
        )

        try:
            familias = importar_familias_canonicas_para_catalogo(
                banco,
                family_keys=faltantes,
                status_catalogo="publicado",
                criado_por_id=int(admin_owner_id) if admin_owner_id else None,
            )
            banco.commit()
        except Exception:
            banco.rollback()
            raise

        banco_dados.logger.info(
            "Bootstrap canônico do catálogo importou %s famílias ausentes (%s já existiam).",
            len(familias),
            len(family_keys_existentes),
        )


def _garantir_empresa_plataforma(
    banco,
    *,
    nome_empresa: str,
    cnpj_empresa: str,
):
    from sqlalchemy import select

    banco_dados = _database_module()

    empresa = banco.scalar(select(banco_dados.Empresa).where(banco_dados.Empresa.cnpj == cnpj_empresa))
    if not empresa:
        empresa = banco_dados.Empresa(
            nome_fantasia=nome_empresa,
            cnpj=cnpj_empresa,
            plano_ativo=banco_dados.PlanoEmpresa.ILIMITADO.value,
            escopo_plataforma=True,
        )
        banco.add(empresa)
        banco.flush()
        return empresa

    empresa.nome_fantasia = nome_empresa
    empresa.plano_ativo = banco_dados.PlanoEmpresa.ILIMITADO.value
    empresa.escopo_plataforma = True
    return empresa


def seed_limites_plano() -> None:
    banco_dados = _database_module()
    with banco_dados.SessaoLocal() as banco:
        for plano_valor, limites in banco_dados.LIMITES_PADRAO.items():
            registro = banco.get(banco_dados.LimitePlano, plano_valor)
            if not registro:
                registro = banco_dados.LimitePlano(plano=plano_valor)
                banco.add(registro)

            for campo, valor in limites.items():
                setattr(registro, campo, valor)

        try:
            banco.commit()
        except Exception:
            banco.rollback()
            raise
