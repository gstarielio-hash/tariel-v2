import { prisma } from "@/lib/server/prisma"

type SettingKey =
  | "admin_reauth_max_age_minutes"
  | "review_ui_canonical"
  | "support_exceptional_mode"
  | "support_exceptional_approval_required"
  | "support_exceptional_justification_required"
  | "support_exceptional_max_duration_minutes"
  | "support_exceptional_scope_level"
  | "default_new_tenant_plan"

type SectionKey =
  | "access"
  | "support"
  | "rollout"
  | "document"
  | "observability"
  | "defaults"

type SettingSource = "database" | "environment" | "default" | "fixed" | "runtime"
type SettingStatusTone = "positive" | "neutral" | "warning" | "critical"
type SettingValue = boolean | number | string

interface PlatformSettingRow {
  chave: SettingKey
  categoria: string
  valor_json: unknown
  motivo_ultima_alteracao: string | null
  atualizada_por_usuario_id: number | null
  criado_em: Date
  atualizado_em: Date | null
  usuarios: {
    id: number
    nome_completo: string
    email: string
  } | null
}

interface RuntimeDescriptor {
  title: string
  description: string
  valueLabel: string
  statusToneKey: SettingStatusTone
  sourceKind: SettingSource
  scopeLabel: string
  technicalPath?: string
  reason?: string
}

interface SectionFormOption {
  value: string
  label: string
}

export interface AdminSettingsFormField {
  name: string
  label: string
  type: "number" | "select" | "checkbox"
  value: string | number | boolean
  displayValue: string
  hint: string
  min?: number
  max?: number
  options?: SectionFormOption[]
}

export interface AdminSettingsFormPreview {
  action: string
  submitLabel: string
  requiresStepUp: boolean
  fields: AdminSettingsFormField[]
}

export interface AdminSettingsItem {
  key?: string
  title: string
  description: string
  valueLabel: string
  sourceLabel: string
  scopeLabel: string
  statusTone: SettingStatusTone
  lastChangedLabel: string
  lastChangedByLabel: string
  reason: string
  impact: string
  technicalPath: string | null
}

export interface AdminSettingsSection {
  key: SectionKey
  title: string
  description: string
  badge: string
  items: AdminSettingsItem[]
  readOnlyNote?: string
  form?: AdminSettingsFormPreview
}

export interface AdminSettingsSummaryCard {
  label: string
  value: string
  hint: string
}

export interface AdminSettingsData {
  summaryCards: AdminSettingsSummaryCard[]
  sections: AdminSettingsSection[]
  metrics: {
    environmentLabel: string
    latestChangedLabel: string
    activePolicies: number
    reviewUiCanonicalLabel: string
    operatorCount: number
    totalItems: number
    editableSections: number
    readOnlySections: number
  }
}

const PLATFORM_ADMIN_ACCESS_LEVEL = 99

const PLATFORM_PLANS = ["Inicial", "Intermediario", "Ilimitado"] as const

const SUPPORT_EXCEPTIONAL_MODE_LABELS = {
  disabled: "Desabilitado",
  approval_required: "Aprovacao obrigatoria",
  incident_controlled: "Incidente controlado",
} as const

const SUPPORT_EXCEPTIONAL_SCOPE_LABELS = {
  metadata_only: "Metadados administrativos",
  administrative: "Suporte administrativo",
  tenant_diagnostic: "Diagnostico de tenant",
} as const

const REVIEW_UI_LABELS = {
  ssr: "SSR legado",
} as const

const SOURCE_LABELS: Record<SettingSource, string> = {
  database: "Configuracao da plataforma",
  environment: "Ambiente",
  default: "Padrao da plataforma",
  fixed: "Regra do portal",
  runtime: "Runtime",
}

const ACCESS_SETTING_DESCRIPTORS = [
  {
    key: "admin_reauth_max_age_minutes",
    title: "Janela de reautenticacao",
    description: "Define a validade do step-up para acoes criticas do Admin-CEO.",
  },
] as const satisfies Array<{
  key: SettingKey
  title: string
  description: string
}>

const SUPPORT_SETTING_DESCRIPTORS = [
  {
    key: "support_exceptional_mode",
    title: "Modo de suporte excepcional",
    description: "Define o regime operacional permitido para suporte fora do fluxo administrativo padrao.",
  },
  {
    key: "support_exceptional_approval_required",
    title: "Aprovacao formal",
    description: "Exige aprovacao explicita antes de ativar suporte excepcional para qualquer tenant.",
  },
  {
    key: "support_exceptional_justification_required",
    title: "Justificativa obrigatoria",
    description: "Impede abertura excepcional sem motivo auditavel e rastreavel.",
  },
  {
    key: "support_exceptional_max_duration_minutes",
    title: "Duracao maxima",
    description: "Janela maxima continua em que um suporte excepcional pode permanecer ativo.",
  },
  {
    key: "support_exceptional_scope_level",
    title: "Escopo maximo permitido",
    description: "Delimita ate onde o suporte excepcional pode alcancar sem violar governanca.",
  },
] as const satisfies Array<{
  key: SettingKey
  title: string
  description: string
}>

const ROLLOUT_SETTING_DESCRIPTORS = [
  {
    key: "review_ui_canonical",
    title: "UI canonica da revisao",
    description: "Fluxo oficial fixado no painel SSR legado do revisor.",
  },
] as const satisfies Array<{
  key: SettingKey
  title: string
  description: string
}>

const DEFAULTS_SETTING_DESCRIPTORS = [
  {
    key: "default_new_tenant_plan",
    title: "Plano padrao do onboarding",
    description: "Plano pre-selecionado ao provisionar uma nova empresa pelo Admin-CEO.",
  },
] as const satisfies Array<{
  key: SettingKey
  title: string
  description: string
}>

const SETTING_DEFINITIONS: Record<
  SettingKey,
  {
    category: string
    type: "int" | "bool" | "enum"
    scopeLabel: string
    min?: number
    max?: number
    allowed?: readonly string[]
    impact: string
  }
> = {
  admin_reauth_max_age_minutes: {
    category: "access",
    type: "int",
    scopeLabel: "Somente Admin-CEO",
    min: 1,
    max: 120,
    impact: "Define por quantos minutos uma reautenticacao TOTP libera acoes criticas.",
  },
  review_ui_canonical: {
    category: "rollout",
    type: "enum",
    scopeLabel: "Revisao e Mesa",
    allowed: ["ssr"],
    impact: "Mantem a revisao no painel SSR legado para preservar um unico fluxo operacional.",
  },
  support_exceptional_mode: {
    category: "support",
    type: "enum",
    scopeLabel: "Todos os tenants",
    allowed: Object.keys(SUPPORT_EXCEPTIONAL_MODE_LABELS),
    impact: "Governa se o suporte excepcional pode ser aberto e em que regime operacional.",
  },
  support_exceptional_approval_required: {
    category: "support",
    type: "bool",
    scopeLabel: "Todos os tenants",
    impact: "Exige aprovacao formal antes de qualquer suporte excepcional autorizado.",
  },
  support_exceptional_justification_required: {
    category: "support",
    type: "bool",
    scopeLabel: "Todos os tenants",
    impact: "Exige justificativa auditavel para toda abertura de suporte excepcional.",
  },
  support_exceptional_max_duration_minutes: {
    category: "support",
    type: "int",
    scopeLabel: "Todos os tenants",
    min: 15,
    max: 1440,
    impact: "Limita a janela maxima, em minutos, para suporte excepcional ativo.",
  },
  support_exceptional_scope_level: {
    category: "support",
    type: "enum",
    scopeLabel: "Todos os tenants",
    allowed: Object.keys(SUPPORT_EXCEPTIONAL_SCOPE_LABELS),
    impact: "Delimita o maior escopo operacional permitido em modo excepcional.",
  },
  default_new_tenant_plan: {
    category: "defaults",
    type: "enum",
    scopeLabel: "Novos tenants",
    allowed: PLATFORM_PLANS,
    impact: "Define o plano selecionado por padrao no onboarding de novas empresas.",
  },
}

const utcDateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: "UTC",
})

function envString(name: string, fallback = "") {
  const value = String(process.env[name] ?? "").trim()
  return value || fallback
}

function envBool(name: string, fallback = false) {
  const value = String(process.env[name] ?? "").trim().toLowerCase()

  if (!value) {
    return fallback
  }

  return ["1", "true", "yes", "sim", "on", "enabled"].includes(value)
}

function envInt(name: string, fallback: number) {
  const value = Number(process.env[name])

  if (!Number.isFinite(value)) {
    return fallback
  }

  return Math.trunc(value)
}

function formatUtcDateTime(value: Date | null | undefined, fallback = "Sem atividade") {
  if (!(value instanceof Date) || Number.isNaN(value.getTime())) {
    return fallback
  }

  return `${utcDateTimeFormatter.format(value).replace(",", "")} UTC`
}

function environmentLabel() {
  return envString("AMBIENTE", envString("NODE_ENV", "desconhecido")).toUpperCase()
}

function normalizeBoolean(value: unknown) {
  if (typeof value === "boolean") {
    return value
  }

  if (typeof value === "number") {
    return value !== 0
  }

  return ["1", "true", "yes", "sim", "on"].includes(String(value ?? "").trim().toLowerCase())
}

function normalizeReviewUiSurface(value: unknown) {
  const normalized = String(value ?? "").trim().toLowerCase()

  if (normalized === "ssr" || normalized === "legacy") {
    return "ssr"
  }

  throw new Error("invalid review ui")
}

function normalizePlan(value: unknown) {
  const normalized = String(value ?? "").trim().toLowerCase()
  const map: Record<string, (typeof PLATFORM_PLANS)[number]> = {
    inicial: "Inicial",
    piloto: "Inicial",
    starter: "Inicial",
    intermediario: "Intermediario",
    pro: "Intermediario",
    profissional: "Intermediario",
    ilimitado: "Ilimitado",
    enterprise: "Ilimitado",
  }

  if (normalized in map) {
    return map[normalized]
  }

  const direct = PLATFORM_PLANS.find((plan) => plan.toLowerCase() === normalized)

  if (direct) {
    return direct
  }

  throw new Error("invalid plan")
}

function latestChangedLabel(rows: PlatformSettingRow[]) {
  let latest: Date | null = null

  for (const row of rows) {
    const candidate = row.atualizado_em ?? row.criado_em

    if (!(candidate instanceof Date) || Number.isNaN(candidate.getTime())) {
      continue
    }

    if (latest == null || candidate > latest) {
      latest = candidate
    }
  }

  return formatUtcDateTime(latest, "Sem mudancas sensiveis")
}

function getPlatformSettingDefault(key: SettingKey): {
  value: SettingValue
  source: SettingSource
} {
  switch (key) {
    case "admin_reauth_max_age_minutes": {
      const source = envString("ADMIN_REAUTH_MAX_AGE_MINUTES") ? "environment" : "default"
      return {
        value: Math.max(envInt("ADMIN_REAUTH_MAX_AGE_MINUTES", 10), 1),
        source,
      }
    }
    case "review_ui_canonical":
      return { value: "ssr", source: "default" }
    case "support_exceptional_mode":
      return { value: "approval_required", source: "default" }
    case "support_exceptional_approval_required":
      return { value: true, source: "default" }
    case "support_exceptional_justification_required":
      return { value: true, source: "default" }
    case "support_exceptional_max_duration_minutes":
      return { value: 120, source: "default" }
    case "support_exceptional_scope_level":
      return { value: "administrative", source: "default" }
    case "default_new_tenant_plan":
      return { value: "Inicial", source: "default" }
  }
}

function coerceSettingValue(key: SettingKey, value: unknown): SettingValue {
  const definition = SETTING_DEFINITIONS[key]

  if (definition.type === "int") {
    const normalized = Number(value)

    if (!Number.isInteger(normalized)) {
      throw new Error("invalid integer")
    }

    if (normalized < Number(definition.min) || normalized > Number(definition.max)) {
      throw new Error("integer outside bounds")
    }

    return normalized
  }

  if (definition.type === "bool") {
    return normalizeBoolean(value)
  }

  if (key === "default_new_tenant_plan") {
    return normalizePlan(value)
  }

  if (key === "review_ui_canonical") {
    return normalizeReviewUiSurface(value)
  }

  const normalized = String(value ?? "").trim().toLowerCase()
  const allowed = definition.allowed ?? []

  if (!allowed.includes(normalized)) {
    throw new Error("invalid enum value")
  }

  return normalized
}

function settingValueLabel(key: SettingKey, value: SettingValue) {
  if (key === "admin_reauth_max_age_minutes") {
    return `${value} min`
  }

  if (key === "review_ui_canonical") {
    return REVIEW_UI_LABELS[String(value) as keyof typeof REVIEW_UI_LABELS] ?? String(value)
  }

  if (key === "support_exceptional_mode") {
    return (
      SUPPORT_EXCEPTIONAL_MODE_LABELS[String(value) as keyof typeof SUPPORT_EXCEPTIONAL_MODE_LABELS] ?? String(value)
    )
  }

  if (key === "support_exceptional_scope_level") {
    return (
      SUPPORT_EXCEPTIONAL_SCOPE_LABELS[String(value) as keyof typeof SUPPORT_EXCEPTIONAL_SCOPE_LABELS] ?? String(value)
    )
  }

  if (key === "support_exceptional_max_duration_minutes") {
    return `${value} min`
  }

  if (typeof value === "boolean") {
    return value ? "Habilitado" : "Desabilitado"
  }

  return String(value)
}

function settingStatusTone(key: SettingKey, value: SettingValue): SettingStatusTone {
  if (
    key === "support_exceptional_mode"
    || key === "support_exceptional_scope_level"
    || key === "support_exceptional_approval_required"
    || key === "support_exceptional_justification_required"
  ) {
    if (key === "support_exceptional_mode") {
      if (value === "disabled") {
        return "neutral"
      }

      if (value === "incident_controlled") {
        return "warning"
      }

      return "positive"
    }

    if (typeof value === "boolean") {
      return value ? "positive" : "warning"
    }

    if (value === "tenant_diagnostic") {
      return "warning"
    }
  }

  if (typeof value === "boolean") {
    return value ? "positive" : "neutral"
  }

  return "neutral"
}

function platformSettingSourceLabel(source: SettingSource) {
  return SOURCE_LABELS[source]
}

function platformSettingSnapshot(
  rowMap: Map<SettingKey, PlatformSettingRow>,
  key: SettingKey,
) {
  const row = rowMap.get(key)

  let source: SettingSource
  let value: SettingValue

  if (row) {
    try {
      value = coerceSettingValue(key, row.valor_json)
      source = "database"
    } catch {
      const fallback = getPlatformSettingDefault(key)
      value = fallback.value
      source = fallback.source
    }
  } else {
    const fallback = getPlatformSettingDefault(key)
    value = fallback.value
    source = fallback.source
  }

  const changedAt = row ? row.atualizado_em ?? row.criado_em : null
  const userName = String(row?.usuarios?.nome_completo ?? "").trim()
  const userEmail = String(row?.usuarios?.email ?? "").trim()
  const actorFallback = row?.atualizada_por_usuario_id ? `Usuario #${row.atualizada_por_usuario_id}` : "Sistema"

  return {
    key,
    value,
    source,
    sourceLabel: platformSettingSourceLabel(source),
    lastChangedLabel: row ? formatUtcDateTime(changedAt, "Sem customizacao") : "Sem customizacao",
    lastChangedByLabel: row ? userName || userEmail || actorFallback : "Padrao da plataforma",
    reason: String(row?.motivo_ultima_alteracao ?? "").trim(),
  }
}

function buildSettingItem(
  rowMap: Map<SettingKey, PlatformSettingRow>,
  key: SettingKey,
  title: string,
  description: string,
  technicalPath?: string,
): AdminSettingsItem {
  const snapshot = platformSettingSnapshot(rowMap, key)
  const definition = SETTING_DEFINITIONS[key]

  return {
    key,
    title,
    description,
    valueLabel: settingValueLabel(key, snapshot.value),
    sourceLabel: snapshot.sourceLabel,
    scopeLabel: definition.scopeLabel,
    statusTone: settingStatusTone(key, snapshot.value),
    lastChangedLabel: snapshot.lastChangedLabel,
    lastChangedByLabel: snapshot.lastChangedByLabel,
    reason: snapshot.reason,
    impact: definition.impact,
    technicalPath: technicalPath ?? null,
  }
}

function buildRuntimeItem(descriptor: RuntimeDescriptor): AdminSettingsItem {
  return {
    title: descriptor.title,
    description: descriptor.description,
    valueLabel: descriptor.valueLabel,
    sourceLabel: platformSettingSourceLabel(descriptor.sourceKind),
    scopeLabel: descriptor.scopeLabel,
    statusTone: descriptor.statusToneKey,
    lastChangedLabel: "Gerenciado pela origem",
    lastChangedByLabel: platformSettingSourceLabel(descriptor.sourceKind),
    reason: descriptor.reason ?? "",
    impact: "",
    technicalPath: descriptor.technicalPath ?? null,
  }
}

function buildRuntimeItems(descriptors: RuntimeDescriptor[]) {
  return descriptors.map((descriptor) => buildRuntimeItem(descriptor))
}

function buildAccessRuntimeDescriptors(operatorCount: number): RuntimeDescriptor[] {
  const googleEnabled = envBool("ADMIN_LOGIN_GOOGLE_ENABLED", false)
  const microsoftEnabled = envBool("ADMIN_LOGIN_MICROSOFT_ENABLED", false)

  return [
    {
      title: "MFA obrigatorio do Admin-CEO",
      description: "O acesso administrativo de plataforma exige TOTP antes da emissao de sessao.",
      valueLabel: "Obrigatorio",
      statusToneKey: "positive",
      sourceKind: "fixed",
      scopeLabel: "Somente Admin-CEO",
    },
    {
      title: "Google corporativo",
      description: "Entrada de identidade autorizada para operadores de plataforma previamente cadastrados.",
      valueLabel: googleEnabled ? "Habilitado" : "Desabilitado",
      statusToneKey: googleEnabled ? "positive" : "neutral",
      sourceKind: "environment",
      scopeLabel: "Somente Admin-CEO",
      technicalPath: "/admin/api/operadores",
      reason: envString("ADMIN_LOGIN_GOOGLE_ENTRYPOINT")
        ? "Gateway configurado."
        : "Gateway ainda nao configurado.",
    },
    {
      title: "Microsoft corporativo",
      description: "Entrada corporativa alternativa para operadores autorizados do Admin-CEO.",
      valueLabel: microsoftEnabled ? "Habilitado" : "Desabilitado",
      statusToneKey: microsoftEnabled ? "positive" : "neutral",
      sourceKind: "environment",
      scopeLabel: "Somente Admin-CEO",
      technicalPath: "/admin/api/operadores",
      reason: envString("ADMIN_LOGIN_MICROSOFT_ENTRYPOINT")
        ? "Gateway configurado."
        : "Gateway ainda nao configurado.",
    },
    {
      title: "Operadores autorizados",
      description: "Total de contas de plataforma autorizadas a acessar o portal Admin-CEO.",
      valueLabel: String(operatorCount),
      statusToneKey: "neutral",
      sourceKind: "runtime",
      scopeLabel: "Somente Admin-CEO",
      technicalPath: "/admin/api/operadores",
    },
  ]
}

function buildRolloutRuntimeDescriptors(): RuntimeDescriptor[] {
  const mobileRolloutEnabled = envBool("TARIEL_V2_ANDROID_ROLLOUT_OBSERVABILITY", false)
  const reportPackEnabled = envBool("TARIEL_V2_REPORT_PACK_ROLLOUT_OBSERVABILITY", true)

  return [
    {
      title: "Observabilidade do Mobile V2",
      description: "Supervisiona rollout movel sem expor conteudo tecnico bruto no Admin-CEO.",
      valueLabel: mobileRolloutEnabled ? "Habilitado" : "Observacao",
      statusToneKey: mobileRolloutEnabled ? "positive" : "neutral",
      sourceKind: "environment",
      scopeLabel: "Mobile e rollout",
      technicalPath: "/admin/api/mobile-v2-rollout/summary",
    },
    {
      title: "Observabilidade do report pack",
      description: "Resume gates, divergencia e queda para Mesa das familias semanticas ja modeladas.",
      valueLabel: reportPackEnabled ? "Habilitada" : "Observacao",
      statusToneKey: reportPackEnabled ? "positive" : "neutral",
      sourceKind: "environment",
      scopeLabel: "Documento e rollout",
      technicalPath: "/admin/api/report-pack-rollout/summary",
    },
  ]
}

function buildDocumentRuntimeDescriptors(): RuntimeDescriptor[] {
  const softGateEnabled = envBool("TARIEL_V2_DOCUMENT_SOFT_GATE", false)
  const hardGateEnabled = envBool("TARIEL_V2_DOCUMENT_HARD_GATE", false)
  const durableEvidenceEnabled =
    envBool("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE", false)
    || Boolean(envString("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR"))

  return [
    {
      title: "Soft gate documental",
      description: "Observa sinais preventivos antes de mutacoes documentais sensiveis.",
      valueLabel: softGateEnabled ? "Habilitado" : "Observacao",
      statusToneKey: softGateEnabled ? "positive" : "neutral",
      sourceKind: "environment",
      scopeLabel: "Documento",
      technicalPath: "/admin/api/document-soft-gate/summary",
    },
    {
      title: "Hard gate documental",
      description: "Resume bloqueios efetivos e o estado operacional do enforcement documental.",
      valueLabel: hardGateEnabled ? "Habilitado" : "Observacao",
      statusToneKey: hardGateEnabled ? "positive" : "warning",
      sourceKind: "environment",
      scopeLabel: "Documento",
      technicalPath: "/admin/api/document-hard-gate/summary",
    },
    {
      title: "Evidencia duravel",
      description: "Mantem trilha persistente de bloqueios documentais para auditoria posterior.",
      valueLabel: durableEvidenceEnabled ? "Habilitada" : "Desabilitada",
      statusToneKey: durableEvidenceEnabled ? "positive" : "neutral",
      sourceKind: "environment",
      scopeLabel: "Documento",
      technicalPath: "/admin/api/document-hard-gate/durable-summary",
    },
  ]
}

function buildObservabilityRuntimeDescriptors(): RuntimeDescriptor[] {
  const replayAllowedInBrowser = envBool("TARIEL_BROWSER_REPLAY_ENABLED", false)
  const logRetentionDays = Math.max(envInt("OBSERVABILITY_LOG_RETENTION_DAYS", 14), 1)
  const perfRetentionDays = Math.max(envInt("OBSERVABILITY_PERF_RETENTION_DAYS", 7), 1)
  const artifactRetentionDays = Math.max(envInt("OBSERVABILITY_ARTIFACT_RETENTION_DAYS", 7), 1)

  return [
    {
      title: "Replay em navegador",
      description: "Indica se a observabilidade permite replay de navegacao no browser.",
      valueLabel: replayAllowedInBrowser ? "Habilitado" : "Desabilitado",
      statusToneKey: replayAllowedInBrowser ? "positive" : "neutral",
      sourceKind: "environment",
      scopeLabel: "Observabilidade",
      technicalPath: "/admin/api/observability/summary",
    },
    {
      title: "Retencao de logs",
      description: "Janela de retencao dos logs administrativos e operacionais minimizados.",
      valueLabel: `${logRetentionDays} dias`,
      statusToneKey: "neutral",
      sourceKind: "environment",
      scopeLabel: "Observabilidade",
    },
    {
      title: "Retencao de performance",
      description: "Janela de retencao de metricas e telemetria de performance da plataforma.",
      valueLabel: `${perfRetentionDays} dias`,
      statusToneKey: "neutral",
      sourceKind: "environment",
      scopeLabel: "Observabilidade",
    },
    {
      title: "Retencao de artifacts",
      description: "Janela de retencao de artifacts e bundles operacionais do runtime.",
      valueLabel: `${artifactRetentionDays} dias`,
      statusToneKey: "neutral",
      sourceKind: "environment",
      scopeLabel: "Observabilidade",
    },
  ]
}

function buildSummaryCards(params: {
  environmentLabel: string
  latestChangedLabel: string
  activePolicies: number
  reviewUiCanonicalLabel: string
}): AdminSettingsSummaryCard[] {
  return [
    {
      label: "Ambiente",
      value: params.environmentLabel,
      hint: "Ambiente em que o portal administrativo esta rodando.",
    },
    {
      label: "Ultima alteracao sensivel",
      value: params.latestChangedLabel,
      hint: "Ultima mudanca salva nas regras da plataforma.",
    },
    {
      label: "Regras ativas",
      value: String(params.activePolicies),
      hint: "Quantidade de regras que estao valendo agora para o Admin-CEO.",
    },
    {
      label: "Liberacao da revisao",
      value: params.reviewUiCanonicalLabel,
      hint: "Tela principal que hoje vale para a Mesa.",
    },
  ]
}

export async function getAdminSettingsData(): Promise<AdminSettingsData> {
  const [rows, operatorCount] = await Promise.all([
    prisma.configuracoes_plataforma.findMany({
      orderBy: [{ categoria: "asc" }, { chave: "asc" }],
      select: {
        chave: true,
        categoria: true,
        valor_json: true,
        motivo_ultima_alteracao: true,
        atualizada_por_usuario_id: true,
        criado_em: true,
        atualizado_em: true,
        usuarios: {
          select: {
            id: true,
            nome_completo: true,
            email: true,
          },
        },
      },
    }) as Promise<PlatformSettingRow[]>,
    prisma.usuarios.count({
      where: {
        account_scope: "platform",
        nivel_acesso: PLATFORM_ADMIN_ACCESS_LEVEL,
      },
    }),
  ])

  const rowMap = new Map(rows.map((row) => [row.chave, row] as const))

  const accessSnapshot = platformSettingSnapshot(rowMap, "admin_reauth_max_age_minutes")
  const supportModeSnapshot = platformSettingSnapshot(rowMap, "support_exceptional_mode")
  const supportApprovalSnapshot = platformSettingSnapshot(rowMap, "support_exceptional_approval_required")
  const supportJustificationSnapshot = platformSettingSnapshot(rowMap, "support_exceptional_justification_required")
  const supportDurationSnapshot = platformSettingSnapshot(rowMap, "support_exceptional_max_duration_minutes")
  const supportScopeSnapshot = platformSettingSnapshot(rowMap, "support_exceptional_scope_level")
  const reviewUiSnapshot = platformSettingSnapshot(rowMap, "review_ui_canonical")
  const defaultPlanSnapshot = platformSettingSnapshot(rowMap, "default_new_tenant_plan")

  const documentRuntimeItems = buildRuntimeItems(buildDocumentRuntimeDescriptors())
  const observabilityRuntimeItems = buildRuntimeItems(buildObservabilityRuntimeDescriptors())
  const rolloutRuntimeItems = buildRuntimeItems(buildRolloutRuntimeDescriptors())

  const sections: AdminSettingsSection[] = [
    {
      key: "access",
      title: "Acesso e seguranca da plataforma",
      description: "Controles de acesso do Admin-CEO, confirmacao extra e protecao das acoes mais sensiveis.",
      badge: "Seguranca",
      items: [
        ...buildRuntimeItems(buildAccessRuntimeDescriptors(operatorCount).slice(0, 1)),
        ...ACCESS_SETTING_DESCRIPTORS.map((descriptor) =>
          buildSettingItem(rowMap, descriptor.key, descriptor.title, descriptor.description),
        ),
        ...buildRuntimeItems(buildAccessRuntimeDescriptors(operatorCount).slice(1)),
      ],
      form: {
        action: "/admin/configuracoes/acesso",
        submitLabel: "Salvar seguranca",
        requiresStepUp: true,
        fields: [
          {
            name: "admin_reauth_max_age_minutes",
            label: "Janela de reautenticacao",
            type: "number",
            value: accessSnapshot.value,
            displayValue: settingValueLabel("admin_reauth_max_age_minutes", accessSnapshot.value),
            min: 1,
            max: 120,
            hint: "Tempo, em minutos, em que a confirmacao extra continua valendo para acoes criticas.",
          },
        ],
      },
    },
    {
      key: "support",
      title: "Politica de suporte excepcional",
      description: "Regras para excecoes administrativas, com duracao, motivo e alcance maximos.",
      badge: "Excecao",
      items: SUPPORT_SETTING_DESCRIPTORS.map((descriptor) =>
        buildSettingItem(rowMap, descriptor.key, descriptor.title, descriptor.description),
      ),
      form: {
        action: "/admin/configuracoes/suporte-excepcional",
        submitLabel: "Salvar politica excepcional",
        requiresStepUp: true,
        fields: [
          {
            name: "support_exceptional_mode",
            label: "Modo operacional",
            type: "select",
            value: supportModeSnapshot.value,
            displayValue: settingValueLabel("support_exceptional_mode", supportModeSnapshot.value),
            hint: "Defina se o suporte fica desligado, depende de aprovacao ou entra em modo de incidente controlado.",
            options: Object.entries(SUPPORT_EXCEPTIONAL_MODE_LABELS).map(([value, label]) => ({
              value,
              label,
            })),
          },
          {
            name: "support_exceptional_approval_required",
            label: "Exigir aprovacao formal",
            type: "checkbox",
            value: supportApprovalSnapshot.value,
            displayValue: settingValueLabel(
              "support_exceptional_approval_required",
              supportApprovalSnapshot.value,
            ),
            hint: "Mantem a excecao condicionada a aprovacao registrada do Admin-CEO.",
          },
          {
            name: "support_exceptional_justification_required",
            label: "Exigir justificativa",
            type: "checkbox",
            value: supportJustificationSnapshot.value,
            displayValue: settingValueLabel(
              "support_exceptional_justification_required",
              supportJustificationSnapshot.value,
            ),
            hint: "Toda excecao precisa registrar o motivo na trilha administrativa.",
          },
          {
            name: "support_exceptional_max_duration_minutes",
            label: "Duracao maxima",
            type: "number",
            value: supportDurationSnapshot.value,
            displayValue: settingValueLabel(
              "support_exceptional_max_duration_minutes",
              supportDurationSnapshot.value,
            ),
            min: 15,
            max: 1440,
            hint: "Tempo maximo continuo em minutos.",
          },
          {
            name: "support_exceptional_scope_level",
            label: "Escopo maximo",
            type: "select",
            value: supportScopeSnapshot.value,
            displayValue: settingValueLabel(
              "support_exceptional_scope_level",
              supportScopeSnapshot.value,
            ),
            hint: "Escolha ate onde o suporte excepcional pode chegar sem abrir conteudo bruto por padrao.",
            options: Object.entries(SUPPORT_EXCEPTIONAL_SCOPE_LABELS).map(([value, label]) => ({
              value,
              label,
            })),
          },
        ],
      },
    },
    {
      key: "rollout",
      title: "Liberacao da revisao",
      description: "Define qual tela de revisao vale como principal e acompanha como ela esta sendo usada.",
      badge: "Liberacao",
      items: [
        ...ROLLOUT_SETTING_DESCRIPTORS.map((descriptor) =>
          buildSettingItem(rowMap, descriptor.key, descriptor.title, descriptor.description),
        ),
        ...rolloutRuntimeItems,
      ],
      form: {
        action: "/admin/configuracoes/rollout",
        submitLabel: "Salvar liberacao",
        requiresStepUp: true,
        fields: [
          {
            name: "review_ui_canonical",
            label: "Tela principal da revisao",
            type: "select",
            value: reviewUiSnapshot.value,
            displayValue: settingValueLabel("review_ui_canonical", reviewUiSnapshot.value),
            hint: "A revisao permanece no SSR legado para manter uma unica tela principal de operacao.",
            options: [{ value: "ssr", label: "SSR legado" }],
          },
        ],
      },
    },
    {
      key: "document",
      title: "Regras do documento",
      description: "Resumo das travas do documento e do que precisa ficar guardado de forma duravel.",
      badge: "Documento",
      items: documentRuntimeItems,
      readOnlyNote:
        "Resumo apenas para consulta. As travas reais do documento sao definidas pelo ambiente e pelas regras centrais.",
    },
    {
      key: "observability",
      title: "Historico e armazenamento",
      description: "Regras de historico e tempo de armazenamento vindas do ambiente da plataforma.",
      badge: "Historico",
      items: observabilityRuntimeItems,
      readOnlyNote:
        "Resumo apenas para consulta. O tempo de armazenamento e o replay desta camada sao definidos fora do portal.",
    },
    {
      key: "defaults",
      title: "Padroes para novas empresas",
      description: "Padroes aplicados quando uma nova empresa e criada no portal.",
      badge: "Onboarding",
      items: DEFAULTS_SETTING_DESCRIPTORS.map((descriptor) =>
        buildSettingItem(rowMap, descriptor.key, descriptor.title, descriptor.description),
      ),
      form: {
        action: "/admin/configuracoes/defaults",
        submitLabel: "Salvar padroes",
        requiresStepUp: true,
        fields: [
          {
            name: "default_new_tenant_plan",
            label: "Plano inicial da nova empresa",
            type: "select",
            value: defaultPlanSnapshot.value,
            displayValue: settingValueLabel("default_new_tenant_plan", defaultPlanSnapshot.value),
            hint: "Plano que ja vem pre-selecionado ao cadastrar uma nova empresa.",
            options: PLATFORM_PLANS.map((value) => ({
              value,
              label: value,
            })),
          },
        ],
      },
    },
  ]

  const replayAllowedInBrowser = envBool("TARIEL_BROWSER_REPLAY_ENABLED", false)
  const hardGateEnabled = envBool("TARIEL_V2_DOCUMENT_HARD_GATE", false)
  const durableEvidenceEnabled =
    envBool("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE", false)
    || Boolean(envString("TARIEL_V2_DOCUMENT_HARD_GATE_DURABLE_EVIDENCE_DIR"))
  const activePolicies =
    Number(replayAllowedInBrowser)
    + Number(hardGateEnabled)
    + Number(durableEvidenceEnabled)
    + Number(supportModeSnapshot.value !== "disabled")

  const summaryCards = buildSummaryCards({
    environmentLabel: environmentLabel(),
    latestChangedLabel: latestChangedLabel(rows),
    activePolicies,
    reviewUiCanonicalLabel: settingValueLabel("review_ui_canonical", reviewUiSnapshot.value),
  })

  const editableSections = sections.filter((section) => section.form).length
  const readOnlySections = sections.length - editableSections
  const totalItems = sections.reduce((sum, section) => sum + section.items.length, 0)

  return {
    summaryCards,
    sections,
    metrics: {
      environmentLabel: summaryCards[0]?.value ?? "DESCONHECIDO",
      latestChangedLabel: summaryCards[1]?.value ?? "Sem mudancas sensiveis",
      activePolicies,
      reviewUiCanonicalLabel: summaryCards[3]?.value ?? "SSR legado",
      operatorCount,
      totalItems,
      editableSections,
      readOnlySections,
    },
  }
}
