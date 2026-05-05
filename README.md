# Implemented Solution: AI-Assisted Call Review System

An internal tool for reviewing and managing call outcomes. The system ingests call transcripts and uses Gemini 1.5 Flash to classify outcomes. It directs ambiguous cases to human reviewers, and tracks final decisions. 

---
## Setup & Instructions to run locally

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # add your GEMINI_API_KEY
python ingest_calls.py
uvicorn main:app --reload
```

To also run AI classification on all calls during ingestion:

```bash
python ingest_calls.py --analyze
```

Get a free Gemini API key at https://aistudio.google.com/apikey — no billing required.
The model used is `gemini-1.5-flash` (1,500 free requests/day).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the FastAPI backend on port 8000.

### Test flow

1. Open the queue — you should see 25 calls (the 20 from the provided dataset + 5 edge cases)
2. Click any call to open the detail view
3. Click **Analyze** to run Gemini classification (requires `GEMINI_API_KEY`)
4. Review the outcome, confidence bar, reasoning, and flags
5. Submit a review with Accept / Reject / Modify + optional notes
6. Return to queue — the call now shows "Reviewed"

---

## Dataset

`data/calls.json` contains 25 calls including 5 edge cases:
- **call_001–020**: The provided dataset (scheduling, payment, support scenarios)
- **call_021**: Non-English speaker (language barrier)
- **call_022**: Severely truncated transcript ("No. Not interested." — 8 seconds)
- **call_023**: Third party answers (husband for wife)
- **call_024**: Payment made but disputed (partial success + compliance risk)
- **call_025**: Vague, non-committal engagement throughout

The original provided dataset is preserved as `data/calls.json`.

---

## Project Structure

```
backend/
  main.py               # FastAPI app + middleware + router mounting
  database.py           # SQLAlchemy engine + session + Base
  models.py             # Call, CallAnalysis, HumanReview (SQLAlchemy ORM)
  schemas.py            # Pydantic request/response models
  outcome_types.py      # taxonomy constants + requires_review() logic
  classifier.py         # Gemini integration
  routes/
    calls.py            # all API route handlers
  ingest_calls.py       # standalone ingestion script

frontend/src/
  types.ts              # shared TypeScript types
  api.ts                # API client
  components/
    Stats/              # aggregate numbers bar
    CallQueue/          # filterable call list
    CallDetail/         # transcript + analysis + review form

data/
  calls.json     # 25 calls (20 origianlly provided + 5 edge cases)
```
---

## Problem Approach

My approach to determine the outcome for each call focuses on:

1. **What happened** — using the outcome taxonomy (11 codes covering all meaningful states)
2. **How certain the outcome is** — using a 0–1 confidence score from the AI classifier
3. **What action to take** — auto-handle or send to human review

And I account for various edge cases. For instance, a call can have a clear outcome (i.e., `CONNECTED_REFUSED`) but still require review because of compliance implications.

---

## Outcome Structure

| Code | Meaning | Auto-handled? |
|------|---------|--------------|
| `NO_ANSWER` | Rang, no pickup | Yes (confidence ≥ 0.85) |
| `VOICEMAIL_LEFT` | Reached voicemail, left message | Yes |
| `VOICEMAIL_NO_MESSAGE` | Reached voicemail, no message left | Yes |
| `CALL_DROPPED` | Technical disconnection mid-call | Yes |
| `WRONG_NUMBER` | Wrong number dialed | Yes |
| `CONNECTED_SUCCESS` | Goal fully achieved | Yes (confidence ≥ 0.85) |
| `CONNECTED_PARTIAL` | Partial progress; follow-up needed | **Always reviewed** |
| `CONNECTED_REFUSED` | Explicit refusal or opt-out | **Always reviewed** (compliance) |
| `CONNECTED_WRONG_PERSON` | Connected but reached wrong person | Yes |
| `CONNECTED_ESCALATION` | Needs escalation to specialist | **Always reviewed** |
| `AMBIGUOUS` | Cannot determine outcome clearly | **Always reviewed** |

**Review triggers** (in priority order):
1. Outcome is `REFUSED`, `ESCALATION`, or `AMBIGUOUS` — always
2. Outcome is `CONNECTED_PARTIAL` — always (follow-up is a human decision)
3. Confidence below 0.70 — always
4. Any flags present — always
5. `NO_ANSWER` or `CONNECTED_SUCCESS` below 0.85 — to prevent false auto-handling

In `calls/outcome_types.py::requires_review()`:
- The `requires_review` decision is computed 
- Outcome codes are validated against a fixed allowlist; unknown codes fall back to `AMBIGUOUS`
- Confidence is clamped to [0, 1] regardless of what the model returns

---

## Handling Ambiguity and Uncertainty

**Several layers protect against overconfident classification:**

- The AI prompt explicitly instructs the model to prefer `AMBIGUOUS` over forcing a weak classification
- Transcripts flagged as very short or corrupted automatically lower the confidence threshold
- `CONNECTED_PARTIAL` is always routed to review, even at high confidence — because "partial" inherently requires a human to decide what happens next
- `CONNECTED_REFUSED` is always routed to review regardless of confidence — because opt-outs have compliance implications that shouldn't be automated away

**Flags** provide extra signal beyond the requires_review decision:
- `compliance-risk` — explicit opt-out, legal language
- `ambiguous-engagement` — person's intent is unclear or contradictory
- `language-barrier` — communication impeded by language
- `incomplete-transcript` — transcript appears truncated or corrupted
- `third-party` — reached someone other than the intended contact
- `partial-success` — some goals achieved but not all
- `classifier-error` — set by the Python layer when parsing fails


---

## AI Usage

* I used Claude Code/Anthropic to assist with setting up routing, UI, and code dependencies to expedite the development and troubleshooting processes for this take-home project. 

- I also integrated Gemini 1.5 Flash to classify all call outcomes.

Gemini API receives:
- The full outcome taxonomy with descriptions
- The call goal
- The call transcript

and returns:
- a structured JSON object including: 
    - outcome code, confidence, reasoning, and flags.


**Why I chose Gemini 1.5 Flash:** The task requires understanding conversational context, user intent, and edge cases (such as with distinguishing "I'll call back later" from "please stop calling"). Gemini 1.5 Flash is great for classifying short-text items and also provides a free tier option.

**Why `temperature=0.1`:** Classification: Low temperature value reduces variance in repeated analyses of the same transcript.

**Failure handling:** If the API call fails or the response can't be parsed, the system returns `{outcome: AMBIGUOUS, confidence: 0, requires_review: true, flags: ["classifier-error"]}`. This ensures failures are always surfaced for human review rather than silently auto-handled.

---

## Tradeoffs I Made

**Used SQLite for Simplicity** I used SQLite for simplicity since it has zero configuration, no installation required, and does not need to be run separately, but this would pose issues with larger sets of data in a production environment.

**Used Gemini 1.5 LLM** Has free tier access and supports long call transcripts without chunking, but occasionally will have malformed JSON output.

**Always-review for partial outcomes.** `CONNECTED_PARTIAL` always requires review even at 99% confidence. This is intentional as partial outcomes involve follow-up decisions that require human judgment. The tradeoff is more review load.

**No multi-label outcomes.** Some calls have multiple relevant outcomes (i.e. payment made + amount disputed). I set the taxonomy to use single primary code and used flags to indicate the other outcomes for simplicity.

**Re-analysis creates a new record.** Clicking "Re-analyze" creates a new `CallAnalysis` row rather than updating the existing one. This preserves the full audit log while the UI always shows the latest analysis.


---

## Failure Cases and Areas for Improvement

The system is usable overall as a prototype but has room for improvement.

1. **SQLite Database** SQLite has zero configuration, no installation required, and does not need to be run separately. In a production system, however I would use PostgreSQL to support multiple concurrent connections and larger data volumes. 

2. **No Proper Authentication** The reviewer name field an input not a login which is suitable for a prototype. In a production system, however, I would need to add proper user authentication and authorization to support role-based permissions.

3. **PII Masking and Data Privacy** Call transcripts may contain Personal Identifiable Information such as names, phone numbers, or payment details. In this prototype, transcripts are sent directly to the LLM and stored without censoring the information which would pose a security issue.

In a production system, I would introduce a PII masking layer before sending data to the model. Sensitive fields would be replaced with placeholders to reduce privacy and compliance risk.

4. **Classification delay** AI classificaton is currently performed synchronously which can cause latency when user and call volume increases so I would move classification to an asynchronous workflow using a task queue like Celery. 

5. **Non-English transcripts.** The model can handle some non-English text but I did not prompt it to handle with multiple language translations. Confidence will often be low in these cases and the `language-barrier` flag should trigger, as demonstrated in `call_021`.

6. **Short transcripts are unreliable.** The model will guess in cases with short transcripts. A 3-word transcript like "No. Not interested." could be a refusal, a dropped call, or a wrong number. (i.e. `call_022`). 

7. **Third-party answers.** When a family member answers, the model must infer that the goal was not achieved with the intended person. This is subtle and the model can mistake it for a partial success. `call_023` demonstrates this.

8. **Ambiguous payment disputes.** `call_024` — payment was collected but the customer is disputing the charge. The "goal" (collect payment) was technically achieved, but there's a compliance risk. The model may classify this as `CONNECTED_SUCCESS` and miss the compliance signal.

9. **Vague, non-committal language.** `call_025` — the person never says yes or no. The model may assign `CONNECTED_PARTIAL` or `AMBIGUOUS`. Both are defensible. The confidence should be low.

10. **API cost at scale.** Every `POST /analyze/` call hits the OpenAI API. At a high volume, this needs batching, caching, or a cheaper model for obvious cases (e.g., empty transcripts).
