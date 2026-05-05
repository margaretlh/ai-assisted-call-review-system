#!/usr/bin/env python
"""
# Ingest sample calls into the database.
"""
import argparse
import json
import sys
from pathlib import Path

import config  # loads .env; must precede any module that reads env vars
from db import SessionLocal, engine, Base
from models import Call, CallAnalysis
from review_service import ReviewService

BASE_DIR = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest calls from a JSON file")
    parser.add_argument("--analyze", action="store_true", help="Run AI classification after ingestion")
    parser.add_argument("--file", default=None, help="Path to JSON file (default: data/calls.json)")
    args = parser.parse_args()

    # Resolve data file
    file_path = Path(args.file) if args.file else BASE_DIR.parent / "data" / "calls.json"
    if not file_path.exists():
        file_path = BASE_DIR.parent / "data" / "calls.json"
    if not file_path.exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    with open(file_path) as f:
        data = json.load(f)

    calls_data = data if isinstance(data, list) else data.get("calls", [])
    print(f"Found {len(calls_data)} calls in {file_path}")

    db = SessionLocal()
    created = skipped = 0

    try:
        for item in calls_data:
            if db.query(Call).filter(Call.external_id == item["id"]).first():
                print(f"  Skipped (exists): {item['id']}")
                skipped += 1
                continue

            call = Call(
                external_id=item["id"],
                goal=item["goal"],
                transcript=item.get("transcript", ""),
                call_metadata=item.get("metadata", {}),
            )
            db.add(call)
            db.commit()
            db.refresh(call)
            print(f"  Created: {item['id']}")
            created += 1

        print(f"\nDone: {created} created, {skipped} skipped")

        if args.analyze:
            if not config.GEMINI_API_KEY:
                print("Error: GEMINI_API_KEY not set — skipping analysis", file=sys.stderr)
                return

            classifier = ReviewService(api_key=config.GEMINI_API_KEY)
            unanalyzed = (
                db.query(Call)
                .filter(Call.id.not_in(db.query(CallAnalysis.call_id).distinct()))
                .all()
            )
            print(f"\nAnalyzing {len(unanalyzed)} calls...")

            for call in unanalyzed:
                print(f"  {call.external_id}...", end=" ", flush=True)
                result = classifier.analyze(call)
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
                print(f"{result['outcome']} ({result['confidence']:.0%})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
