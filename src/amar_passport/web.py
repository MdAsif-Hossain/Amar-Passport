"""Amar Passport — Web UI server (FastAPI + embedded frontend)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from amar_passport.models import ApplicantProfile, ReadinessFacts
from amar_passport.report import render_markdown
from amar_passport.repository import PassportKnowledgeBase
from amar_passport.rules import evaluate_profile

load_dotenv()

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Amar Passport", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main UI."""
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/assess")
async def assess(request: Request) -> JSONResponse:
    """Run the deterministic rules engine and return structured facts."""
    try:
        body = await request.json()
        profile = ApplicantProfile.model_validate(body)
    except (json.JSONDecodeError, ValidationError) as exc:
        return JSONResponse(
            status_code=422,
            content={"error": f"Invalid profile: {exc}"},
        )

    try:
        knowledge, data_source = PassportKnowledgeBase().load(prefer_remote=False)
        facts = evaluate_profile(profile, knowledge, data_source)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": f"Policy engine error: {exc}"},
        )

    # Return structured JSON for the frontend to render beautifully
    return JSONResponse(content=_facts_to_response(facts))


@app.post("/api/crew")
async def crew_run(request: Request) -> JSONResponse:
    """Run the full CrewAI pipeline and return the LLM-enhanced report."""
    try:
        body = await request.json()
        profile = ApplicantProfile.model_validate(body)
    except (json.JSONDecodeError, ValidationError) as exc:
        return JSONResponse(
            status_code=422,
            content={"error": f"Invalid profile: {exc}"},
        )

    try:
        knowledge, data_source = PassportKnowledgeBase().load(prefer_remote=False)
        facts = evaluate_profile(profile, knowledge, data_source)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": f"Policy engine error: {exc}"},
        )

    model = os.getenv("MODEL")
    api_key_present = any(
        os.getenv(k)
        for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY")
    )

    if not model or not api_key_present:
        # No API key configured → return deterministic report
        return JSONResponse(
            content={
                **_facts_to_response(facts),
                "crew_report": render_markdown(facts),
                "mode": "offline",
                "mode_reason": "No API key configured. Using deterministic engine.",
            }
        )

    try:
        from amar_passport.crew import run_passport_crew

        crew_report = run_passport_crew(facts, model=model)
        return JSONResponse(
            content={
                **_facts_to_response(facts),
                "crew_report": crew_report,
                "mode": "online",
            }
        )
    except Exception as exc:
        # Fallback to deterministic
        return JSONResponse(
            content={
                **_facts_to_response(facts),
                "crew_report": render_markdown(facts),
                "mode": "fallback",
                "mode_reason": f"CrewAI failed ({type(exc).__name__}). Using deterministic engine.",
            }
        )


def _facts_to_response(facts: ReadinessFacts) -> dict[str, Any]:
    """Convert ReadinessFacts to a frontend-friendly JSON dict."""
    e = facts.eligibility
    f = facts.fee
    return {
        "eligibility": {
            "permitted_validity_years": e.permitted_validity_years,
            "selected_validity_years": e.selected_validity_years,
            "permitted_page_counts": e.permitted_page_counts,
            "selected_page_count": e.selected_page_count,
            "identification_en": e.identification_requirement_en,
            "identification_bn": e.identification_requirement_bn,
            "conflicts_en": e.conflicts_en,
            "conflicts_bn": e.conflicts_bn,
            "advisories_en": e.advisories_en,
            "advisories_bn": e.advisories_bn,
        },
        "fee": {
            "requested_delivery": f.requested_delivery.value,
            "charged_delivery_tier": f.charged_delivery_tier.value,
            "delivery_time": f.delivery_time,
            "delivery_time_bn": f.delivery_time_bn,
            "base_fee_bdt": f.base_fee_bdt,
            "vat_rate": f.vat_rate,
            "vat_bdt": f.vat_bdt,
            "total_fee_bdt": f.total_fee_bdt,
            "benefit_note": f.benefit_note,
            "benefit_note_bn": f.benefit_note_bn,
        },
        "documents": [
            {"en": doc.en, "bn": doc.bn} for doc in facts.documents
        ],
        "warnings_en": facts.warnings_en,
        "warnings_bn": facts.warnings_bn,
        "audit": {
            "data_source": facts.data_source,
            "data_version": facts.data_version,
            "source_urls": facts.source_urls,
        },
        "markdown_report": render_markdown(facts),
    }


def main():
    """Entry point for `amar-passport-web` command."""
    import sys
    import uvicorn

    # Reconfigure for Windows terminals so emoji/Bangla is not mangled
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    port = int(os.getenv("PORT", "8000"))
    print(f"\n  Amar Passport Web UI")
    print(f"  -------------------------")
    print(f"  Open: http://localhost:{port}\n")
    uvicorn.run(
        "amar_passport.web:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
