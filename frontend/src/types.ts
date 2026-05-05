export type OutcomeCode =
  | "NO_ANSWER"
  | "VOICEMAIL_LEFT"
  | "VOICEMAIL_NO_MESSAGE"
  | "CALL_DROPPED"
  | "WRONG_NUMBER"
  | "CONNECTED_SUCCESS"
  | "CONNECTED_PARTIAL"
  | "CONNECTED_REFUSED"
  | "CONNECTED_WRONG_PERSON"
  | "CONNECTED_ESCALATION"
  | "AMBIGUOUS";

export const OUTCOME_LABELS: Record<OutcomeCode, string> = {
  NO_ANSWER: "No Answer",
  VOICEMAIL_LEFT: "Voicemail – Left Message",
  VOICEMAIL_NO_MESSAGE: "Voicemail – No Message",
  CALL_DROPPED: "Call Dropped",
  WRONG_NUMBER: "Wrong Number",
  CONNECTED_SUCCESS: "Success",
  CONNECTED_PARTIAL: "Partial",
  CONNECTED_REFUSED: "Refused / Opt-Out",
  CONNECTED_WRONG_PERSON: "Wrong Person",
  CONNECTED_ESCALATION: "Escalation",
  AMBIGUOUS: "Ambiguous",
};

export type ReviewAction = "accept" | "reject" | "modify";

export interface CallAnalysis {
  id: number;
  outcome: OutcomeCode;
  confidence: number;
  reasoning: string;
  flags: string[];
  requires_review: boolean;
  created_at: string;
}

export interface HumanReview {
  id: number;
  action: ReviewAction;
  final_outcome: OutcomeCode;
  notes: string;
  reviewer_name: string;
  reviewed_at: string;
}

export interface CallSummary {
  id: string;
  external_id: string;
  goal: string;
  metadata: Record<string, unknown>;
  created_at: string;
  latest_analysis: CallAnalysis | null;
  latest_review: HumanReview | null;
  is_reviewed: boolean;
}

export interface CallDetail extends CallSummary {
  transcript: string;
  analyses: CallAnalysis[];
}

export interface Stats {
  total: number;
  pending_review: number;
  reviewed_today: number;
  analyzed: number;
  not_analyzed: number;
}

export interface ReviewPayload {
  action: ReviewAction;
  final_outcome: OutcomeCode;
  notes?: string;
  reviewer_name?: string;
}
