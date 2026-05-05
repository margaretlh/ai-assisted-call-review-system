import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../../api";
import type { CallDetail as CallDetailType, OutcomeCode, ReviewAction } from "../../types";
import { OUTCOME_LABELS } from "../../types";
import styles from "./CallDetail.module.css";

export default function CallDetail() {
  const { id } = useParams<{ id: string }>();
  const [call, setCall] = useState<CallDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const reload = () => {
    if (!id) return;
    setLoading(true);
    setError(null); // clear stale error before each fetch
    api
      .getCall(id)
      .then(setCall)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(reload, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAnalyze = async () => {
    if (!id) return;
    setAnalyzing(true);
    try {
      await api.analyzeCall(id);
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAnalyzing(false);
    }
  };

  if (!id) return <div className={styles.error}>Invalid call URL.</div>;
  if (loading) return <div className={styles.loading}>Loading…</div>;
  if (error) return <div className={styles.error}>{error}</div>;
  if (!call) return null;

  const analysis = call.analyses[0] ?? null;
  const review = call.latest_review;

  return (
    <div className={styles.container}>
      <div className={styles.breadcrumb}>
        <Link to="/" className={styles.backLink}>← Queue</Link>
        <span className={styles.externalId}>{call.external_id}</span>
      </div>

      <div className={styles.grid}>
        {/* Left: transcript */}
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Transcript</h2>
          <div className={styles.goalBadge}>
            <span className={styles.goalLabel}>Goal</span>
            <span>{call.goal}</span>
          </div>
          {call.metadata && Object.keys(call.metadata).length > 0 && (
            <div className={styles.metaRow}>
              {Object.entries(call.metadata).map(([k, v]) => (
                <span key={k} className={styles.metaChip}>
                  {k}: {String(v)}
                </span>
              ))}
            </div>
          )}
          <pre className={styles.transcript}>{call.transcript}</pre>
        </section>

        {/* Right: analysis + review */}
        <div className={styles.rightCol}>
          <section className={styles.card}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>AI Analysis</h2>
              <button
                className={styles.analyzeBtn}
                onClick={handleAnalyze}
                disabled={analyzing}
              >
                {analyzing ? "Analyzing…" : analysis ? "Re-analyze" : "Analyze"}
              </button>
            </div>

            {analysis ? (
              <div className={styles.analysis}>
                <div className={styles.outcomeRow}>
                  <OutcomePill outcome={analysis.outcome} />
                  <ConfidenceMeter value={analysis.confidence} />
                </div>

                {analysis.flags.length > 0 && (
                  <div className={styles.flags}>
                    {analysis.flags.map((f) => (
                      <span key={f} className={styles.flag}>{f}</span>
                    ))}
                  </div>
                )}

                <div className={styles.reviewAlert}>
                  {analysis.requires_review ? (
                    <span className={styles.reviewRequired}>⚠ Requires human review</span>
                  ) : (
                    <span className={styles.reviewAuto}>✓ Can be auto-handled</span>
                  )}
                </div>

                <div className={styles.reasoning}>
                  <h3 className={styles.reasoningTitle}>Reasoning</h3>
                  <p>{analysis.reasoning}</p>
                </div>
              </div>
            ) : (
              <p className={styles.noAnalysis}>
                No analysis yet. Click "Analyze" to run AI classification.
              </p>
            )}
          </section>

          {/* Review form / result */}
          {review ? (
            <ReviewResult review={review} />
          ) : (
            analysis && (
              <ReviewForm callId={call.id} initialOutcome={analysis.outcome} onSubmit={reload} />
            )
          )}
        </div>
      </div>
    </div>
  );
}

function OutcomePill({ outcome }: { outcome: string }) {
  const label = OUTCOME_LABELS[outcome as OutcomeCode] ?? outcome;
  return <span className={`${styles.outcomePill} ${getOutcomeClass(outcome, styles)}`}>{label}</span>;
}

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const cls = value >= 0.85 ? styles.confHigh : value >= 0.7 ? styles.confMid : styles.confLow;
  return (
    <div className={styles.confidence}>
      <div className={styles.confTrack}>
        <div className={`${styles.confFill} ${cls}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={styles.confLabel}>{pct}% confidence</span>
    </div>
  );
}

function ReviewResult({ review }: { review: NonNullable<CallDetailType["latest_review"]> }) {
  return (
    <section className={`${styles.card} ${styles.reviewCard}`}>
      <h2 className={styles.cardTitle}>Human Review</h2>
      <div className={styles.reviewResult}>
        <div className={styles.reviewResultRow}>
          <span className={styles.reviewLabel}>Action</span>
          <span className={`${styles.actionBadge} ${styles[`action_${review.action}`]}`}>
            {review.action.toUpperCase()}
          </span>
        </div>
        <div className={styles.reviewResultRow}>
          <span className={styles.reviewLabel}>Final Outcome</span>
          <OutcomePill outcome={review.final_outcome} />
        </div>
        {review.reviewer_name && (
          <div className={styles.reviewResultRow}>
            <span className={styles.reviewLabel}>Reviewer</span>
            <span>{review.reviewer_name}</span>
          </div>
        )}
        {review.notes && (
          <div className={styles.reviewNotes}>
            <span className={styles.reviewLabel}>Notes</span>
            <p>{review.notes}</p>
          </div>
        )}
        <p className={styles.reviewDate}>
          {new Date(review.reviewed_at).toLocaleString()}
        </p>
      </div>
    </section>
  );
}

function ReviewForm({
  callId,
  initialOutcome,
  onSubmit,
}: {
  callId: string;
  initialOutcome: OutcomeCode;
  onSubmit: () => void;
}) {
  const [action, setAction] = useState<ReviewAction>("accept");
  const [finalOutcome, setFinalOutcome] = useState<OutcomeCode>(initialOutcome);

  // useState ignores prop changes after the first render, so sync explicitly
  // when initialOutcome changes (e.g. after re-analysis).
  useEffect(() => {
    setFinalOutcome(initialOutcome);
  }, [initialOutcome]);
  const [notes, setNotes] = useState("");
  const [reviewerName, setReviewerName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.submitReview(callId, {
        action,
        final_outcome: finalOutcome,
        notes,
        reviewer_name: reviewerName,
      });
      onSubmit();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className={`${styles.card} ${styles.reviewCard}`}>
      <h2 className={styles.cardTitle}>Submit Review</h2>
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.formGroup}>
          <label className={styles.label}>Action</label>
          <div className={styles.actionBtns}>
            {(["accept", "reject", "modify"] as ReviewAction[]).map((a) => (
              <button
                key={a}
                type="button"
                className={`${styles.actionToggle} ${action === a ? styles[`actionToggle_${a}`] : ""}`}
                onClick={() => setAction(a)}
              >
                {a.charAt(0).toUpperCase() + a.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.formGroup}>
          <label className={styles.label} htmlFor="outcome">Final Outcome</label>
          <select
            id="outcome"
            className={styles.select}
            value={finalOutcome}
            onChange={(e) => setFinalOutcome(e.target.value as OutcomeCode)}
          >
            {Object.entries(OUTCOME_LABELS).map(([code, label]) => (
              <option key={code} value={code}>{label}</option>
            ))}
          </select>
        </div>

        <div className={styles.formGroup}>
          <label className={styles.label} htmlFor="reviewer">Reviewer Name (optional)</label>
          <input
            id="reviewer"
            className={styles.input}
            value={reviewerName}
            onChange={(e) => setReviewerName(e.target.value)}
            placeholder="Your name"
          />
        </div>

        <div className={styles.formGroup}>
          <label className={styles.label} htmlFor="notes">Notes (optional)</label>
          <textarea
            id="notes"
            className={styles.textarea}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="Any observations or corrections…"
          />
        </div>

        {error && <div className={styles.formError}>{error}</div>}

        <button type="submit" className={styles.submitBtn} disabled={submitting}>
          {submitting ? "Submitting…" : "Submit Review"}
        </button>
      </form>
    </section>
  );
}

function getOutcomeClass(outcome: string, s: Record<string, string>): string {
  const map: Record<string, string> = {
    CONNECTED_SUCCESS: s.outcomePillSuccess,
    CONNECTED_REFUSED: s.outcomePillDanger,
    CONNECTED_ESCALATION: s.outcomePillDanger,
    AMBIGUOUS: s.outcomePillWarning,
    CONNECTED_PARTIAL: s.outcomePillWarning,
  };
  return map[outcome] ?? s.outcomePillNeutral;
}
