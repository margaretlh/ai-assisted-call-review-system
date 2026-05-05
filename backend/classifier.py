"""
Gemini AI classifier for call outcome classification.
"""
import json
import logging
import google.generativeai as genai
from outcome_types import OUTCOME_DESCRIPTIONS, OUTCOME_CHOICES, AMBIGUOUS

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a call outcome classifier for a call review system.

Given a call goal and transcript, classify the outcome using EXACTLY one of these codes:

{taxonomy}

Return a JSON object with these fields:
- outcome: one of the codes above (string)
- confidence: float between 0.0 and 1.0
- reasoning: 1-3 sentence explanation of your classification
- flags: list of strings describing notable issues (empty list if none). Use these flag values when applicable:
  * "compliance-risk" — explicit opt-out, legal language, or regulatory concern
  * "ambiguous-engagement" — person's intent is unclear or contradictory
  * "language-barrier" — communication impeded by language
  * "incomplete-transcript" — transcript appears truncated or too short to be reliable
  * "third-party" — person who answered is not the intended contact
  * "partial-success" — some but not all goals achieved
  * "classifier-error" — used only by the system, not you

Guidelines:
- Be conservative: prefer AMBIGUOUS over forcing a weak classification
- If the transcript is very short or garbled, lower your confidence and add "incomplete-transcript"
- If the person opts out or objects, always use CONNECTED_REFUSED
- If the call needs escalation, always use CONNECTED_ESCALATION
- Confidence should reflect how certain you are, not how well the call went

CALL GOAL:
{goal}

TRANSCRIPT:
{transcript}"""

TAXONOMY_TEXT = "\n".join(
    f"  {code}: {desc}" for code, desc in OUTCOME_DESCRIPTIONS.items()
)

_VALID_CODES = {code for code, _ in OUTCOME_CHOICES}


class CallClassifier:
    """ Uses the Gemini API to return a structured classification result.
    returns:
        {
            outcome: str,
            confidence: float,
            reasoning: str,
            flags: list[str],
            raw_ai_response: dict,
        }
    """

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

    def classify(self, call) -> dict:
        """Call Gemini and return the parsed, validated classification."""
        try:
            return self._call_api(call)
        except Exception as exc:
            logger.error("Classifier error for call %s: %s", call.external_id, exc)
            return self._error_result(str(exc))

    def _call_api(self, call) -> dict:
        prompt = PROMPT_TEMPLATE.format(
            taxonomy=TAXONOMY_TEXT,
            goal=call.goal,
            transcript=call.transcript or "(empty — no transcript recorded)",
        )

        response = self.model.generate_content(prompt)
        raw_text = response.text
        parsed = json.loads(raw_text)

        outcome = parsed.get("outcome", AMBIGUOUS)
        confidence = float(parsed.get("confidence", 0.0))
        reasoning = parsed.get("reasoning", "")
        flags = parsed.get("flags", [])

        # Validate outcome code — unknown codes fall back to AMBIGUOUS
        if outcome not in _VALID_CODES:
            logger.warning("AI returned unknown outcome %r, falling back to AMBIGUOUS", outcome)
            outcome = AMBIGUOUS
            confidence = min(confidence, 0.5)
            flags = list(set(flags) | {"classifier-error"})

        # Clamp confidence to [0, 1]
        confidence = max(0.0, min(1.0, confidence))

        return {
            "outcome": outcome,
            "confidence": confidence,
            "reasoning": reasoning,
            "flags": flags,
            "raw_ai_response": {"text": raw_text},
        }

    @staticmethod
    def _error_result(error_msg: str) -> dict:
        return {
            "outcome": AMBIGUOUS,
            "confidence": 0.0,
            "reasoning": f"Classification failed: {error_msg}",
            "flags": ["classifier-error"],
            "raw_ai_response": {"error": error_msg},
        }
