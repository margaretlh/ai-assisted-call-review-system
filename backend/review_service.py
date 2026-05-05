"""
Review service layer between the AI classifier and the routes to decide whether a call needs human review. 
"""
import logging
from classifier import CallClassifier
from outcome_types import requires_review, AMBIGUOUS

logger = logging.getLogger(__name__)


# Runs AI classification
class ReviewService:
    def __init__(self, api_key: str):
        self._classifier = CallClassifier(api_key=api_key)

    def analyze(self, call) -> dict:
        result = self._classifier.classify(call)

        # requires_review is enforced here in Python — the AI has no say in it.
        review_needed = requires_review(
            outcome=result["outcome"],
            confidence=result["confidence"],
            flags=result["flags"],
        )

        return {**result, "requires_review": review_needed}

    @staticmethod
    def error_result(error_msg: str) -> dict:
        """Fallback used when the service itself cannot be instantiated."""
        return {
            "outcome": AMBIGUOUS,
            "confidence": 0.0,
            "reasoning": f"Review service unavailable: {error_msg}",
            "flags": ["classifier-error"],
            "requires_review": True,
            "raw_ai_response": {"error": error_msg},
        }
