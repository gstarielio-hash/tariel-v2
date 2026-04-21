import { MaterialCommunityIcons } from "@expo/vector-icons";
import {
  ActivityIndicator,
  Image,
  Modal,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";

import type { ApiHealthStatus } from "../../types/mobile";
import { colors } from "../../theme/tokens";
import { styles } from "../InspectorMobileApp.styles";
import type { AttachmentPickerOptionDescriptor } from "../chat/attachmentPolicy";
import type {
  MobileActivityNotification,
  OfflinePendingMessage,
} from "../chat/types";
import type {
  OfflineQueueFilter,
  SessionModalsStackFilter,
} from "./SessionModalsStack";
import {
  buildActivityCenterAutomationMarkerIds,
  buildActivityCenterAutomationProbeLabel,
  type ActivityCenterAutomationDiagnostics,
} from "./mobilePilotAutomationDiagnostics";

type IconName = keyof typeof MaterialCommunityIcons.glyphMap;

export function AttachmentPickerModal({
  options,
  visible,
  onClose,
  onChoose,
}: {
  options: AttachmentPickerOptionDescriptor[];
  visible: boolean;
  onClose: () => void;
  onChoose: (option: "camera" | "galeria" | "documento") => void;
}) {
  return (
    <Modal
      animationType="fade"
      onRequestClose={onClose}
      transparent
      visible={visible}
    >
      <View style={styles.activityModalBackdrop}>
        <View style={styles.activityModalCard}>
          <View style={styles.activityModalHeader}>
            <View style={styles.activityModalCopy}>
              <Text style={styles.activityModalEyebrow}>anexar</Text>
              <Text style={styles.activityModalTitle}>Escolha o anexo</Text>
              <Text style={styles.activityModalDescription}>
                Fotos entram direto no caso. Documentos seguem a politica do
                fluxo ativo.
              </Text>
            </View>
            <Pressable onPress={onClose} style={styles.activityModalClose}>
              <MaterialCommunityIcons
                name="close"
                size={20}
                color={colors.textPrimary}
              />
            </Pressable>
          </View>

          <View style={styles.actionList}>
            {options.map((item) => (
              <Pressable
                key={item.key}
                disabled={!item.enabled}
                onPress={() => onChoose(item.key)}
                style={[
                  styles.actionItem,
                  !item.enabled ? styles.actionItemDisabled : null,
                ]}
                testID={`attachment-picker-option-${item.key}`}
              >
                <MaterialCommunityIcons
                  name={item.icon}
                  size={20}
                  color={item.enabled ? colors.accent : colors.textMuted}
                />
                <View style={styles.actionItemCopy}>
                  <Text
                    style={[
                      styles.actionText,
                      !item.enabled ? styles.actionTextDisabled : null,
                    ]}
                  >
                    {item.title}
                  </Text>
                  <Text style={styles.actionItemDetail}>{item.detail}</Text>
                </View>
              </Pressable>
            ))}
          </View>
        </View>
      </View>
    </Modal>
  );
}

export function ActivityCenterModal({
  activityCenterAutomationDiagnostics,
  automationDiagnosticsEnabled,
  visible,
  onClose,
  monitorandoAtividade,
  notificacoes,
  onAbrirNotificacao,
  formatarHorarioAtividade,
}: {
  activityCenterAutomationDiagnostics: ActivityCenterAutomationDiagnostics;
  automationDiagnosticsEnabled: boolean;
  visible: boolean;
  onClose: () => void;
  monitorandoAtividade: boolean;
  notificacoes: readonly MobileActivityNotification[];
  onAbrirNotificacao: (item: MobileActivityNotification) => void;
  formatarHorarioAtividade: (value: string) => string;
}) {
  const automationMarkerIds = automationDiagnosticsEnabled
    ? buildActivityCenterAutomationMarkerIds(
        activityCenterAutomationDiagnostics,
      )
    : [];
  const automationProbeLabel = automationDiagnosticsEnabled
    ? buildActivityCenterAutomationProbeLabel(
        activityCenterAutomationDiagnostics,
      )
    : "";

  return (
    <Modal
      animationType="slide"
      onRequestClose={onClose}
      transparent
      visible={visible}
    >
      <View style={styles.activityModalBackdrop} testID="activity-center-modal">
        <View style={styles.activityModalCard} testID="activity-center-card">
          {automationDiagnosticsEnabled ? (
            <View
              accessible
              collapsable={false}
              pointerEvents="none"
              style={{
                alignItems: "flex-end",
                position: "absolute",
                top: 4,
                right: 4,
                width: 6,
                zIndex: 9999,
              }}
              testID="activity-center-automation-probe"
              accessibilityLabel={automationProbeLabel}
            >
              {automationMarkerIds.map((markerId, index) => (
                <View
                  accessibilityLabel={markerId}
                  collapsable={false}
                  key={markerId}
                  style={{
                    backgroundColor: "rgba(255,255,255,0.02)",
                    borderRadius: 1,
                    height: 2,
                    marginTop: index === 0 ? 0 : 1,
                    width: 2,
                  }}
                  testID={markerId}
                />
              ))}
            </View>
          ) : null}

          <View style={styles.activityModalHeader}>
            <View style={styles.activityModalCopy}>
              <Text style={styles.activityModalEyebrow}>
                Central do inspetor
              </Text>
              <Text style={styles.activityModalTitle}>
                Central de atividade
              </Text>
              <Text style={styles.activityModalDescription}>
                Alertas recentes do laudo ativo e da mesa enquanto o app estiver
                em uso.
              </Text>
            </View>
            <Pressable
              onPress={onClose}
              style={styles.activityModalClose}
              testID="activity-center-close-button"
            >
              <MaterialCommunityIcons
                name="close"
                size={18}
                color={colors.textPrimary}
              />
            </Pressable>
          </View>

          {monitorandoAtividade ? (
            <View
              style={styles.activityModalLoading}
              testID="activity-center-loading"
            >
              <ActivityIndicator size="small" color={colors.accent} />
              <Text style={styles.activityModalLoadingText}>
                Atualizando atividade...
              </Text>
            </View>
          ) : null}

          <ScrollView
            contentContainerStyle={styles.activityModalList}
            testID="activity-center-list"
          >
            {notificacoes.length ? (
              notificacoes.map((item) => (
                <Pressable
                  key={item.id}
                  onPress={() => onAbrirNotificacao(item)}
                  testID={`activity-center-item-${item.id}`}
                  style={[
                    styles.activityItem,
                    item.unread ? styles.activityItemUnread : null,
                  ]}
                >
                  <View style={styles.activityItemIcon}>
                    <MaterialCommunityIcons
                      name={
                        item.kind === "status"
                          ? "progress-clock"
                          : item.kind === "mesa_resolvida"
                            ? "check-decagram-outline"
                            : item.kind === "mesa_reaberta"
                              ? "alert-circle-outline"
                              : "message-text-outline"
                      }
                      size={18}
                      color={colors.accent}
                    />
                  </View>
                  <View style={styles.activityItemBody}>
                    <View style={styles.activityItemTop}>
                      <Text style={styles.activityItemTitle}>{item.title}</Text>
                      <Text style={styles.activityItemTime}>
                        {formatarHorarioAtividade(item.createdAt)}
                      </Text>
                    </View>
                    <Text style={styles.activityItemText}>{item.body}</Text>
                    <Text style={styles.activityItemHint}>
                      {item.targetThread === "mesa"
                        ? "Abrir na aba Mesa"
                        : "Abrir no Chat"}
                    </Text>
                  </View>
                </Pressable>
              ))
            ) : (
              <View
                style={styles.activityEmptyState}
                testID="activity-center-empty-state"
              >
                <MaterialCommunityIcons
                  name="bell-outline"
                  size={26}
                  color={colors.textSecondary}
                />
                <Text style={styles.activityEmptyTitle}>
                  Nenhuma atividade recente
                </Text>
                <Text style={styles.activityEmptyText}>
                  Quando a mesa responder ou um laudo mudar de status, isso
                  aparece aqui.
                </Text>
              </View>
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

export function OfflineQueueModal({
  visible,
  onClose,
  resumoFilaOfflineFiltrada,
  sincronizandoFilaOffline,
  podeSincronizarFilaOffline,
  sincronizacaoDispositivos,
  statusApi,
  onSincronizarFilaOffline,
  filtrosFilaOffline,
  filtroFilaOffline,
  onSetFiltroFilaOffline,
  filaOfflineFiltrada,
  filaOfflineOrdenadaTotal,
  sincronizandoItemFilaId,
  onSincronizarItemFilaOffline,
  onRetomarItemFilaOffline,
  onRemoverItemFilaOffline,
  formatarHorarioAtividade,
  iconePendenciaOffline,
  resumoPendenciaOffline,
  legendaPendenciaOffline,
  rotuloStatusPendenciaOffline,
  detalheStatusPendenciaOffline,
  pendenciaFilaProntaParaReenvio,
}: {
  visible: boolean;
  onClose: () => void;
  resumoFilaOfflineFiltrada: string;
  sincronizandoFilaOffline: boolean;
  podeSincronizarFilaOffline: boolean;
  sincronizacaoDispositivos: boolean;
  statusApi: ApiHealthStatus;
  onSincronizarFilaOffline: () => void;
  filtrosFilaOffline: readonly SessionModalsStackFilter[];
  filtroFilaOffline: OfflineQueueFilter;
  onSetFiltroFilaOffline: (key: OfflineQueueFilter) => void;
  filaOfflineFiltrada: readonly OfflinePendingMessage[];
  filaOfflineOrdenadaTotal: number;
  sincronizandoItemFilaId: string;
  onSincronizarItemFilaOffline: (item: OfflinePendingMessage) => void;
  onRetomarItemFilaOffline: (item: OfflinePendingMessage) => void;
  onRemoverItemFilaOffline: (id: string) => void;
  formatarHorarioAtividade: (value: string) => string;
  iconePendenciaOffline: (item: OfflinePendingMessage) => IconName;
  resumoPendenciaOffline: (item: OfflinePendingMessage) => string;
  legendaPendenciaOffline: (item: OfflinePendingMessage) => string;
  rotuloStatusPendenciaOffline: (item: OfflinePendingMessage) => string;
  detalheStatusPendenciaOffline: (item: OfflinePendingMessage) => string;
  pendenciaFilaProntaParaReenvio: (item: OfflinePendingMessage) => boolean;
}) {
  return (
    <Modal
      animationType="slide"
      onRequestClose={onClose}
      transparent
      visible={visible}
    >
      <View style={styles.activityModalBackdrop}>
        <View style={styles.activityModalCard}>
          <View style={styles.activityModalHeader}>
            <View style={styles.activityModalCopy}>
              <Text style={styles.activityModalEyebrow}>Fila local</Text>
              <Text style={styles.activityModalTitle}>Fila offline</Text>
              <Text style={styles.activityModalDescription}>
                Envios guardados localmente para o inspetor retomar, revisar ou
                reenviar quando a conexão voltar.
              </Text>
            </View>
            <Pressable onPress={onClose} style={styles.activityModalClose}>
              <MaterialCommunityIcons
                name="close"
                size={18}
                color={colors.textPrimary}
              />
            </Pressable>
          </View>

          <View style={styles.offlineModalToolbar}>
            <Text style={styles.offlineModalToolbarText}>
              {resumoFilaOfflineFiltrada}
            </Text>
            {sincronizandoFilaOffline ? (
              <ActivityIndicator size="small" color={colors.accent} />
            ) : (
              <Pressable
                disabled={!podeSincronizarFilaOffline}
                onPress={onSincronizarFilaOffline}
                style={[
                  styles.offlineModalSyncButton,
                  !podeSincronizarFilaOffline
                    ? styles.offlineModalSyncButtonDisabled
                    : null,
                ]}
              >
                <MaterialCommunityIcons
                  name={
                    podeSincronizarFilaOffline
                      ? "upload-outline"
                      : !sincronizacaoDispositivos
                        ? "sync-off"
                        : statusApi === "online"
                          ? "timer-sand"
                          : "cloud-off-outline"
                  }
                  size={16}
                  color={
                    podeSincronizarFilaOffline
                      ? colors.accent
                      : colors.textSecondary
                  }
                />
                <Text
                  style={[
                    styles.offlineModalSyncText,
                    !podeSincronizarFilaOffline
                      ? styles.offlineModalSyncTextDisabled
                      : null,
                  ]}
                >
                  Sincronizar
                </Text>
              </Pressable>
            )}
          </View>
          {!sincronizacaoDispositivos ? (
            <Text style={styles.offlineModalToolbarText}>
              Sincronização entre dispositivos está desativada nas configurações
              de dados.
            </Text>
          ) : null}

          <View style={styles.offlineModalFilters}>
            {filtrosFilaOffline.map((filtro) => {
              const ativo = filtroFilaOffline === filtro.key;
              return (
                <Pressable
                  key={filtro.key}
                  onPress={() => onSetFiltroFilaOffline(filtro.key)}
                  style={[
                    styles.offlineModalFilterChip,
                    ativo ? styles.offlineModalFilterChipActive : null,
                  ]}
                >
                  <Text
                    style={[
                      styles.offlineModalFilterText,
                      ativo ? styles.offlineModalFilterTextActive : null,
                    ]}
                  >
                    {filtro.label}
                  </Text>
                  <View
                    style={[
                      styles.offlineModalFilterCount,
                      ativo ? styles.offlineModalFilterCountActive : null,
                    ]}
                  >
                    <Text
                      style={[
                        styles.offlineModalFilterCountText,
                        ativo ? styles.offlineModalFilterCountTextActive : null,
                      ]}
                    >
                      {filtro.count}
                    </Text>
                  </View>
                </Pressable>
              );
            })}
          </View>

          <ScrollView contentContainerStyle={styles.activityModalList}>
            {filaOfflineFiltrada.length ? (
              filaOfflineFiltrada.map((item) => (
                <View
                  key={`offline-modal-${item.id}`}
                  style={styles.offlineModalItem}
                >
                  <View style={styles.offlineModalItemTop}>
                    <View style={styles.offlineModalItemBadge}>
                      <MaterialCommunityIcons
                        name={iconePendenciaOffline(item)}
                        size={16}
                        color={item.lastError ? colors.danger : colors.accent}
                      />
                    </View>
                    <View style={styles.offlineModalItemCopy}>
                      <View style={styles.offlineModalItemHeading}>
                        <Text style={styles.offlineModalItemTitle}>
                          {item.channel === "mesa" ? "Mesa" : "Chat"} •{" "}
                          {item.title}
                        </Text>
                        <Text style={styles.offlineModalItemTime}>
                          {formatarHorarioAtividade(item.createdAt)}
                        </Text>
                      </View>
                      <Text style={styles.offlineModalItemText}>
                        {resumoPendenciaOffline(item)}
                      </Text>
                      <Text style={styles.offlineModalItemHint}>
                        {legendaPendenciaOffline(item)}
                      </Text>
                      <View style={styles.offlineModalItemStatusRow}>
                        <View
                          style={[
                            styles.offlineModalItemStatusBadge,
                            item.lastError
                              ? styles.offlineModalItemStatusBadgeError
                              : null,
                          ]}
                        >
                          <MaterialCommunityIcons
                            name={
                              item.lastError
                                ? "alert-circle-outline"
                                : "clock-outline"
                            }
                            size={13}
                            color={
                              item.lastError ? colors.danger : colors.accent
                            }
                          />
                          <Text
                            style={[
                              styles.offlineModalItemStatusBadgeText,
                              item.lastError
                                ? styles.offlineModalItemStatusBadgeTextError
                                : null,
                            ]}
                          >
                            {rotuloStatusPendenciaOffline(item)}
                          </Text>
                        </View>
                        <Text style={styles.offlineModalItemStatusText}>
                          {detalheStatusPendenciaOffline(item)}
                        </Text>
                      </View>
                    </View>
                  </View>

                  <View style={styles.offlineModalItemActions}>
                    <Pressable
                      disabled={
                        !sincronizacaoDispositivos ||
                        statusApi !== "online" ||
                        sincronizandoFilaOffline ||
                        Boolean(sincronizandoItemFilaId)
                      }
                      onPress={() => onSincronizarItemFilaOffline(item)}
                      style={[
                        styles.offlineModalActionGhost,
                        !sincronizacaoDispositivos ||
                        statusApi !== "online" ||
                        sincronizandoFilaOffline ||
                        Boolean(sincronizandoItemFilaId)
                          ? styles.offlineModalActionGhostDisabled
                          : null,
                      ]}
                    >
                      {sincronizandoItemFilaId === item.id ? (
                        <ActivityIndicator size="small" color={colors.accent} />
                      ) : (
                        <MaterialCommunityIcons
                          name={
                            pendenciaFilaProntaParaReenvio(item)
                              ? "upload-outline"
                              : "lightning-bolt-outline"
                          }
                          size={16}
                          color={colors.accent}
                        />
                      )}
                      <Text
                        style={[
                          styles.offlineModalActionGhostText,
                          !sincronizacaoDispositivos ||
                          statusApi !== "online" ||
                          sincronizandoFilaOffline ||
                          Boolean(sincronizandoItemFilaId)
                            ? styles.offlineModalActionGhostTextDisabled
                            : null,
                        ]}
                      >
                        {pendenciaFilaProntaParaReenvio(item)
                          ? "Enviar agora"
                          : "Forçar agora"}
                      </Text>
                    </Pressable>
                    <Pressable
                      onPress={() => onRetomarItemFilaOffline(item)}
                      style={styles.offlineModalActionPrimary}
                    >
                      <MaterialCommunityIcons
                        name="reply-outline"
                        size={16}
                        color={colors.white}
                      />
                      <Text style={styles.offlineModalActionPrimaryText}>
                        Retomar
                      </Text>
                    </Pressable>
                    <Pressable
                      onPress={() => onRemoverItemFilaOffline(item.id)}
                      style={styles.offlineModalActionSecondary}
                    >
                      <MaterialCommunityIcons
                        name="close"
                        size={15}
                        color={colors.textSecondary}
                      />
                      <Text style={styles.offlineModalActionSecondaryText}>
                        Remover
                      </Text>
                    </Pressable>
                  </View>
                </View>
              ))
            ) : (
              <View style={styles.activityEmptyState}>
                <MaterialCommunityIcons
                  name={
                    filaOfflineOrdenadaTotal
                      ? "filter-variant"
                      : "cloud-check-outline"
                  }
                  size={26}
                  color={colors.textSecondary}
                />
                <Text style={styles.activityEmptyTitle}>
                  {filaOfflineOrdenadaTotal
                    ? "Nenhuma pendência neste filtro"
                    : "Fila offline vazia"}
                </Text>
                <Text style={styles.activityEmptyText}>
                  {filaOfflineOrdenadaTotal
                    ? "Troque entre Tudo, Chat e Mesa para localizar a pendência certa mais rápido."
                    : "Quando o app guardar um envio local, ele aparece aqui para você retomar ou sincronizar depois."}
                </Text>
              </View>
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

export function AttachmentPreviewModal({
  visible,
  onClose,
  title,
  uri,
  accessToken,
}: {
  visible: boolean;
  onClose: () => void;
  title: string;
  uri: string;
  accessToken: string;
}) {
  return (
    <Modal
      animationType="fade"
      onRequestClose={onClose}
      transparent
      visible={visible}
    >
      <View style={styles.attachmentModalBackdrop}>
        <View style={styles.attachmentModalCard}>
          <View style={styles.attachmentModalHeader}>
            <Text numberOfLines={1} style={styles.attachmentModalTitle}>
              {title || "Imagem anexada"}
            </Text>
            <Pressable onPress={onClose} style={styles.attachmentModalClose}>
              <MaterialCommunityIcons
                name="close"
                size={18}
                color={colors.white}
              />
            </Pressable>
          </View>

          {uri && accessToken ? (
            <Image
              resizeMode="contain"
              source={{
                uri,
                headers: {
                  Authorization: `Bearer ${accessToken}`,
                },
              }}
              style={styles.attachmentModalImage}
            />
          ) : null}
        </View>
      </View>
    </Modal>
  );
}
