"""
The system uses the following Outcome taxonomy for call classification 
to classify calls via Geminiand decide if human review is required.
"""

# Outcome codes
NO_ANSWER = "NO_ANSWER"
VOICEMAIL_LEFT = "VOICEMAIL_LEFT"
VOICEMAIL_NO_MESSAGE = "VOICEMAIL_NO_MESSAGE"
CALL_DROPPED = "CALL_DROPPED"
WRONG_NUMBER = "WRONG_NUMBER"
CONNECTED_SUCCESS = "CONNECTED_SUCCESS"
CONNECTED_PARTIAL = "CONNECTED_PARTIAL"
CONNECTED_REFUSED = "CONNECTED_REFUSED"
CONNECTED_WRONG_PERSON = "CONNECTED_WRONG_PERSON"
CONNECTED_ESCALATION = "CONNECTED_ESCALATION"
AMBIGUOUS = "AMBIGUOUS"

OUTCOME_CHOICES = [
    (NO_ANSWER, "No Answer"),
    (VOICEMAIL_LEFT, "Voicemail – Message Left"),
    (VOICEMAIL_NO_MESSAGE, "Voicemail – No Message"),
    (CALL_DROPPED, "Call Dropped"),
    (WRONG_NUMBER, "Wrong Number"),
    (CONNECTED_SUCCESS, "Connected – Success"),
    (CONNECTED_PARTIAL, "Connected – Partial"),
    (CONNECTED_REFUSED, "Connected – Refused / Opt-Out"),
    (CONNECTED_WRONG_PERSON, "Connected – Wrong Person"),
    (CONNECTED_ESCALATION, "Connected – Escalation Needed"),
    (AMBIGUOUS, "Ambiguous"),
]

# Outcomes that always require human review regardless of confidence
ALWAYS_REVIEW = {CONNECTED_REFUSED, CONNECTED_ESCALATION, AMBIGUOUS}

# Outcomes that require review only when confidence is below threshold
REVIEW_IF_LOW_CONFIDENCE = {CONNECTED_PARTIAL}

# Confidence thresholds
AUTO_HANDLE_CONFIDENCE_THRESHOLD = 0.70  # below this → always review
HIGH_CONFIDENCE_THRESHOLD = 0.85         # needed for auto-handling NO_ANSWER / SUCCESS

# Descriptions fed into the AI prompt
OUTCOME_DESCRIPTIONS = {
    NO_ANSWER: "Phone rang but nobody picked up. No voicemail reached.",
    VOICEMAIL_LEFT: "Call reached a voicemail system and an agent left a message.",
    VOICEMAIL_NO_MESSAGE: "Call reached a voicemail system but no message was left.",
    CALL_DROPPED: "Call connected briefly but was cut off by a technical issue before resolution.",
    WRONG_NUMBER: "Call reached someone or a business that is not the intended contact.",
    CONNECTED_SUCCESS: "Call connected to the right person and the stated goal was fully achieved.",
    CONNECTED_PARTIAL: (
        "Call connected to the right person and partial progress was made "
        "(e.g. agreed to call back, needs to think about it, follow-up required)."
    ),
    CONNECTED_REFUSED: (
        "Call connected and the person explicitly refused or opted out. "
        "Always flagged for compliance review."
    ),
    CONNECTED_WRONG_PERSON: (
        "Call connected but reached someone other than the intended contact "
        "(e.g. family member, assistant, different employee)."
    ),
    CONNECTED_ESCALATION: (
        "Call connected but the situation requires escalation to a supervisor or specialist. "
        "Always flagged for human review."
    ),
    AMBIGUOUS: (
        "The transcript is unclear, contradictory, or too incomplete to assign a confident outcome. "
        "Always flagged for review."
    ),
}


def requires_review(outcome: str, confidence: float, flags: list) -> bool:
    """
    Determine whether a call analysis requires human review.
    """
    if outcome in ALWAYS_REVIEW:
        return True
    if confidence < AUTO_HANDLE_CONFIDENCE_THRESHOLD:
        return True
    if flags:
        return True
    if outcome in REVIEW_IF_LOW_CONFIDENCE:
        return True
    # NO_ANSWER and CONNECTED_SUCCESS need high confidence to auto-handle
    if outcome in {NO_ANSWER, CONNECTED_SUCCESS} and confidence < HIGH_CONFIDENCE_THRESHOLD:
        return True
    return False
