import { Text, View } from "react-native";

import type { MobileReviewPackage } from "../../types/mobile";
import { styles } from "../InspectorMobileApp.styles";
import {
  lerRegistro,
  lerTexto,
  resumirIntegridadePdfOficial,
} from "./ThreadConversationReviewCardUtils";

export function renderizarDocumentoEmitidoCard(
  reviewPackage: MobileReviewPackage | null | undefined,
  caseLifecycleStatus: string | undefined,
  testID = "chat-issued-document-card",
) {
  const review = lerRegistro(reviewPackage);
  const emissaoOficial = lerRegistro(review?.emissao_oficial);
  const currentIssue = lerRegistro(emissaoOficial?.current_issue);
  const verification = lerRegistro(review?.public_verification);
  const issueNumber = lerTexto(currentIssue?.issue_number);
  const issueState = lerTexto(currentIssue?.issue_state_label, "Emitido");
  const issuedAt = lerTexto(currentIssue?.issued_at);
  const verificationUrl = lerTexto(verification?.verification_url);
  const issueIntegrity = resumirIntegridadePdfOficial(
    emissaoOficial,
    currentIssue,
  );
  const emitted = caseLifecycleStatus === "emitido";

  if (!emitted && !issueNumber && !verificationUrl) {
    return null;
  }

  return (
    <View style={styles.threadReviewCard} testID={testID}>
      <Text style={styles.threadReviewEyebrow}>documento emitido</Text>
      <Text style={styles.threadReviewTitle}>
        {issueNumber || "PDF final governado"}
      </Text>
      <Text style={styles.threadReviewDescription}>
        {issueIntegrity.diverged
          ? "O PDF atual divergiu do documento emitido. Gere uma nova emissão antes de distribuir a versão atual."
          : emitted
            ? "O caso já foi emitido. Reabra apenas se precisar iniciar um novo ciclo técnico."
            : "A emissão oficial já está registrada para este caso."}
      </Text>
      <View style={styles.threadReviewMetaGrid}>
        <View style={styles.threadReviewMetaItem}>
          <Text style={styles.threadReviewMetaLabel}>Estado</Text>
          <Text style={styles.threadReviewMetaValue}>{issueState}</Text>
        </View>
        <View style={styles.threadReviewMetaItem}>
          <Text style={styles.threadReviewMetaLabel}>Emitido em</Text>
          <Text style={styles.threadReviewMetaValue}>
            {issuedAt || "Rastreado"}
          </Text>
        </View>
      </View>
      {issueIntegrity.summary ? (
        <View style={styles.threadReviewWarningItem}>
          <Text style={styles.threadReviewWarningTitle}>
            {issueIntegrity.title}
          </Text>
          <Text style={styles.threadReviewWarningText}>
            {issueIntegrity.summary}
            {issueIntegrity.versionDetail
              ? ` ${issueIntegrity.versionDetail}.`
              : ""}
          </Text>
        </View>
      ) : null}
      {verificationUrl ? (
        <Text style={styles.threadReviewFootnote}>
          Verificação pública: {verificationUrl}
        </Text>
      ) : null}
    </View>
  );
}
