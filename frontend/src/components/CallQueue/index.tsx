import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import type { CallSummary } from "../../types";
import { OUTCOME_LABELS } from "../../types";
import styles from "./CallQueue.module.css";

type Filter = "all" | "pending" | "reviewed";

export default function CallQueue() {
  const [calls, setCalls] = useState<CallSummary[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null); // clear stale error from a previous filter tab
    api
      .getCalls({ status: filter })
      .then(setCalls)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filter]);

  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <h2 className={styles.title}>Call Queue</h2>
        <div className={styles.filters}>
          {(["all", "pending", "reviewed"] as Filter[]).map((f) => (
            <button
              key={f}
              className={`${styles.filterBtn} ${filter === f ? styles.filterBtnActive : ""}`}
              onClick={() => setFilter(f)}
            >
              {f === "all" ? "All" : f === "pending" ? "Needs Review" : "Reviewed"}
            </button>
          ))}
        </div>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {loading ? (
        <div className={styles.empty}>Loading…</div>
      ) : calls.length === 0 ? (
        <div className={styles.empty}>No calls found.</div>
      ) : (
        <div className={styles.list}>
          {calls.map((call) => (
            <CallRow key={call.id} call={call} />
          ))}
        </div>
      )}
    </div>
  );
}

function CallRow({ call }: { call: CallSummary }) {
  const analysis = call.latest_analysis;
  const review = call.latest_review;

  return (
    <Link to={`/calls/${call.id}`} className={styles.row}>
      <div className={styles.rowLeft}>
        <span className={styles.externalId}>{call.external_id}</span>
        <span className={styles.goal}>{call.goal}</span>
      </div>

      <div className={styles.rowRight}>
        {analysis ? (
          <>
            <OutcomeBadge outcome={analysis.outcome} />
            <ConfidenceBar value={analysis.confidence} />
          </>
        ) : (
          <span className={styles.noAnalysis}>Not analyzed</span>
        )}
        <ReviewStatus review={review} requiresReview={analysis?.requires_review} />
      </div>
    </Link>
  );
}

function OutcomeBadge({ outcome }: { outcome: string }) {
  const label = OUTCOME_LABELS[outcome as keyof typeof OUTCOME_LABELS] ?? outcome;
  const cls = getOutcomeClass(outcome);
  return <span className={`${styles.badge} ${styles[cls]}`}>{label}</span>;
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const cls = value >= 0.85 ? "high" : value >= 0.7 ? "medium" : "low";
  return (
    <div className={styles.confidenceWrap} title={`Confidence: ${pct}%`}>
      <div className={`${styles.confidenceBar} ${styles[`conf_${cls}`]}`} style={{ width: `${pct}%` }} />
      <span className={styles.confidenceLabel}>{pct}%</span>
    </div>
  );
}

function ReviewStatus({
  review,
  requiresReview,
}: {
  review: CallSummary["latest_review"];
  requiresReview?: boolean;
}) {
  if (review) {
    return <span className={`${styles.statusBadge} ${styles.statusReviewed}`}>Reviewed</span>;
  }
  if (requiresReview) {
    return <span className={`${styles.statusBadge} ${styles.statusPending}`}>Needs Review</span>;
  }
  return <span className={`${styles.statusBadge} ${styles.statusAuto}`}>Auto-handled</span>;
}

function getOutcomeClass(outcome: string): string {
  const map: Record<string, string> = {
    CONNECTED_SUCCESS: "badgeSuccess",
    CONNECTED_REFUSED: "badgeDanger",
    CONNECTED_ESCALATION: "badgeDanger",
    AMBIGUOUS: "badgeWarning",
    CONNECTED_PARTIAL: "badgeWarning",
    NO_ANSWER: "badgeNeutral",
    VOICEMAIL_LEFT: "badgeNeutral",
    VOICEMAIL_NO_MESSAGE: "badgeNeutral",
    CALL_DROPPED: "badgeNeutral",
    WRONG_NUMBER: "badgeNeutral",
    CONNECTED_WRONG_PERSON: "badgeNeutral",
  };
  return map[outcome] ?? "badgeNeutral";
}
