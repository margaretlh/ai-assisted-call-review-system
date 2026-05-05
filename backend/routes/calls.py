from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

import config
from db import get_db
from models import Call, CallAnalysis, HumanReview
from schemas import (
    CallAnalysisOut,
    CallDetailOut,
    CallSummaryOut,
    HumanReviewOut,
    IngestBatchIn,
    IngestOut,
    ReviewIn,
    StatsOut,
)
from review_service import ReviewService
from outcome_types import OUTCOME_CHOICES

router = APIRouter()


# ── service singleton ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _review_service() -> ReviewService:
    """Instantiated once per process. lru_cache ensures the Gemini client is reused."""
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")
    return ReviewService(api_key=config.GEMINI_API_KEY)


def _get_review_service() -> ReviewService:
    try:
        return _review_service()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# ── helpers ───────────────────────────────────────────────────────────────────

def _latest_analysis(call: Call) -> CallAnalysis | None:
    if not call.analyses:
        return None
    return max(call.analyses, key=lambda a: a.created_at)


def _latest_review(call: Call) -> HumanReview | None:
    if not call.reviews:
        return None
    return max(call.reviews, key=lambda r: r.reviewed_at)


def _build_summary(call: Call) -> dict:
    la = _latest_analysis(call)
    lr = _latest_review(call)
    return {
        "id": call.id,
        "external_id": call.external_id,
        "goal": call.goal,
        "metadata": call.call_metadata or {},
        "created_at": call.created_at,
        "latest_analysis": CallAnalysisOut.model_validate(la) if la else None,
        "latest_review": HumanReviewOut.model_validate(lr) if lr else None,
        "is_reviewed": lr is not None,
    }


# ── routes ────────────────────────────────────────────────────────────────────

@router.get("/calls/stats/", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Call.id)).scalar() or 0
    analyzed = (
        db.query(func.count(Call.id))
        .filter(Call.id.in_(db.query(CallAnalysis.call_id).distinct()))
        .scalar() or 0
    )

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    reviewed_today = (
        db.query(func.count(HumanReview.id))
        .filter(HumanReview.reviewed_at >= today_start)
        .scalar() or 0
    )

    reviewed_call_ids = db.query(HumanReview.call_id).distinct()
    pending_review = (
        db.query(func.count(Call.id.distinct()))
        .join(CallAnalysis, Call.id == CallAnalysis.call_id)
        .filter(CallAnalysis.requires_review.is_(True))
        .filter(Call.id.not_in(reviewed_call_ids))
        .scalar() or 0
    )

    return StatsOut(
        total=total,
        pending_review=pending_review,
        reviewed_today=reviewed_today,
        analyzed=analyzed,
        not_analyzed=total - analyzed,
    )


@router.get("/calls/", response_model=list[CallSummaryOut])
def list_calls(
    status: str = Query(default="all", pattern="^(all|pending|reviewed)$"),
    db: Session = Depends(get_db),
):
    calls = (
        db.query(Call)
        .options(selectinload(Call.analyses), selectinload(Call.reviews))
        .order_by(Call.created_at.desc())
        .all()
    )

    result = []
    for call in calls:
        la = _latest_analysis(call)
        lr = _latest_review(call)

        if status == "pending":
            if not (la and la.requires_review and lr is None):
                continue
        elif status == "reviewed":
            if lr is None:
                continue

        result.append(_build_summary(call))

    return result


@router.get("/calls/{call_id}/", response_model=CallDetailOut)
def get_call(call_id: str, db: Session = Depends(get_db)):
    call = (
        db.query(Call)
        .options(selectinload(Call.analyses), selectinload(Call.reviews))
        .filter(Call.id == call_id)
        .first()
    )
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    analyses_sorted = sorted(call.analyses, key=lambda a: a.created_at, reverse=True)
    return {
        **_build_summary(call),
        "transcript": call.transcript,
        "analyses": [CallAnalysisOut.model_validate(a) for a in analyses_sorted],
    }


@router.post("/calls/{call_id}/analyze/", response_model=CallAnalysisOut, status_code=201)
def analyze_call(
    call_id: str,
    db: Session = Depends(get_db),
    svc: ReviewService = Depends(_get_review_service),
):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    result = svc.analyze(call)

    try:
        analysis = CallAnalysis(
            call_id=call.id,
            outcome=result["outcome"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            flags=result["flags"],
            requires_review=result["requires_review"],
            raw_ai_response=result["raw_ai_response"],
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
    except Exception:
        db.rollback()
        raise

    return CallAnalysisOut.model_validate(analysis)


@router.post("/calls/{call_id}/review/", response_model=HumanReviewOut, status_code=201)
def review_call(call_id: str, body: ReviewIn, db: Session = Depends(get_db)):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    valid_outcomes = {code for code, _ in OUTCOME_CHOICES}
    if body.final_outcome not in valid_outcomes:
        raise HTTPException(status_code=422, detail=f"Invalid outcome: {body.final_outcome}")
    if body.action not in {"accept", "reject", "modify"}:
        raise HTTPException(status_code=422, detail=f"Invalid action: {body.action}")

    latest_analysis = (
        db.query(CallAnalysis)
        .filter(CallAnalysis.call_id == call_id)
        .order_by(CallAnalysis.created_at.desc())
        .first()
    )

    try:
        review = HumanReview(
            call_id=call.id,
            analysis_id=latest_analysis.id if latest_analysis else None,
            action=body.action,
            final_outcome=body.final_outcome,
            notes=body.notes,
            reviewer_name=body.reviewer_name,
        )
        db.add(review)
        db.commit()
        db.refresh(review)
    except Exception:
        db.rollback()
        raise

    return HumanReviewOut.model_validate(review)


@router.post("/ingest/", response_model=IngestOut)
def ingest_calls(body: IngestBatchIn, db: Session = Depends(get_db)):
    created = 0
    skipped = 0
    errors: list[dict] = []

    for item in body.calls:
        try:
            if db.query(Call).filter(Call.external_id == item.id).first():
                skipped += 1
                continue
            call = Call(
                external_id=item.id,
                goal=item.goal,
                transcript=item.transcript,
                call_metadata=item.metadata,
            )
            db.add(call)
            db.commit()
            created += 1
        except Exception as exc:
            db.rollback()
            errors.append({"id": item.id, "error": str(exc)})

    return IngestOut(created=created, skipped=skipped, errors=errors)
