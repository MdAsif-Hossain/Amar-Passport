from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from amar_passport.crew import run_passport_crew
from amar_passport.models import ApplicantProfile
from amar_passport.report import render_markdown
from amar_passport.repository import PROJECT_ROOT, PassportKnowledgeBase
from amar_passport.rules import evaluate_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="amar-passport",
        description="Generate a bilingual Bangladesh e-Passport readiness report.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--profile", type=Path, help="Path to an applicant JSON profile")
    source.add_argument(
        "--demo",
        choices=["adult", "minor"],
        help="Run a bundled demonstration profile",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use deterministic rendering without an LLM (still exercises all policy rules)",
    )
    parser.add_argument(
        "--local-data-only",
        action="store_true",
        help="Skip the official fee-page refresh and use the versioned local database",
    )
    parser.add_argument("--model", help="CrewAI model override, e.g. openai/gpt-4o-mini")
    parser.add_argument("--output", type=Path, help="Optional path for the Markdown report")
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    profile_path = _resolve_profile_path(args.profile, args.demo)

    try:
        with profile_path.open("r", encoding="utf-8") as handle:
            profile = ApplicantProfile.model_validate(json.load(handle))
        knowledge, data_source = PassportKnowledgeBase().load(
            prefer_remote=not args.local_data_only
        )
        facts = evaluate_profile(profile, knowledge, data_source)
    except (OSError, json.JSONDecodeError, ValidationError, RuntimeError) as exc:
        print(f"Input/data error: {exc}", file=sys.stderr)
        return 2

    if args.offline:
        report = render_markdown(facts)
    else:
        model = args.model or os.getenv("MODEL")
        try:
            report = run_passport_crew(facts, model=model)
        except Exception as exc:
            print(
                f"CrewAI run failed ({type(exc).__name__}: {exc}). "
                "Returning the deterministic fallback report.",
                file=sys.stderr,
            )
            report = render_markdown(facts)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        # Reconfigure Windows terminals so Bangla output is not encoded as cp1252.
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(report)
    return 0


def _resolve_profile_path(profile: Path | None, demo: str | None) -> Path:
    if profile is not None:
        return profile
    filename = "adult_private.json" if demo == "adult" else "minor_inconsistent.json"
    return PROJECT_ROOT / "examples" / filename


if __name__ == "__main__":
    raise SystemExit(main())

