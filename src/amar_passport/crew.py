from __future__ import annotations

import json
from typing import Any

from amar_passport.models import ReadinessFacts


async def run_passport_crew(facts: ReadinessFacts, model: str | None = None) -> str:
    """Run the three-agent sequential crew and return its final Markdown report."""

    try:
        from crewai import Agent, Crew, Process, Task
    except ImportError as exc:
        raise RuntimeError(
            "CrewAI is not installed. Run `pip install -e .` or use `--offline`."
        ) from exc

    shared: dict[str, Any] = {"verbose": True, "allow_delegation": False}
    if model:
        shared["llm"] = model

    policy_guardian = Agent(
        role="Bangladesh Passport Policy Expert — The Policy Guardian",
        goal=(
            "Audit age eligibility, permitted validity and page count, and the correct "
            "NID/BRC requirement without overriding official deterministic facts."
        ),
        backstory=(
            "You are a meticulous former consular policy reviewer. You know that a helpful "
            "answer must also be an auditable one: age boundaries are checked explicitly, "
            "outdated policy assumptions are called out, and inconsistent requests are never "
            "silently accepted."
        ),
        **shared,
    )
    fee_calculator = Agent(
        role="Financial Auditor — The Chancellor of the Exchequer",
        goal=(
            "Verify the exact BDT fee, its 15% VAT component, and delivery tier using only "
            "the supplied 2026 fee facts and the Policy Guardian's eligible configuration."
        ),
        backstory=(
            "You are a public-fee auditor who reconciles every number before publication. "
            "You never estimate a statutory fee, never double-add VAT, and clearly disclose "
            "when an eligible government employee receives an NOC-based service benefit."
        ),
        **shared,
    )
    document_architect = Agent(
        role="Documentation Officer — The Document Architect",
        goal=(
            "Turn the policy and fee findings into a complete bilingual readiness report with "
            "a customized document checklist and visible inconsistencies."
        ),
        backstory=(
            "You have reviewed thousands of enrolment files. You translate complex consular "
            "requirements into calm, precise English and Bangla checklists, while retaining "
            "source provenance and reminding applicants that the passport office has final authority."
        ),
        **shared,
    )

    facts_json = json.dumps(facts.model_dump(mode="json"), ensure_ascii=False, indent=2)

    policy_task = Task(
        description=(
            "Review the deterministic case facts below. Explain the permitted validity, page "
            "count, identification rule, corrections, and policy advisories. Treat every supplied "
            "number and conflict as authoritative; do not invent or alter policy.\n\n"
            f"CASE FACTS:\n{facts_json}"
        ),
        expected_output=(
            "A concise policy finding listing selected validity/pages, identification requirement, "
            "and every inconsistency or advisory."
        ),
        agent=policy_guardian,
    )

    fee_task = Task(
        description=(
            "Using the Policy Guardian's eligible configuration as context, audit the supplied fee. "
            "State requested delivery, charged tier, delivery time, base fee, 15% VAT, total BDT, "
            "and any NOC benefit. Copy the deterministic monetary values exactly.\n\n"
            f"DETERMINISTIC FEE FACTS:\n{facts.fee.model_dump_json(indent=2)}"
        ),
        expected_output="A reconciled fee statement in BDT whose base plus VAT equals the total.",
        agent=fee_calculator,
        context=[policy_task],
    )

    report_task = Task(
        description=(
            "Create the final Passport Readiness Report from the policy and fee context plus the "
            "deterministic case facts. Output Markdown only. Include an English section with one "
            "two-column Markdown table (Category | Recommendation), followed by a Bangla section "
            "with one two-column table (বিষয় | সুপারিশ). Both tables must include eligibility, "
            "recommended passport, identification, delivery, fee before VAT, VAT, total fee, "
            "documents, and flags. Preserve all warnings verbatim. End with data source, version, "
            "official URLs, and this disclaimer: Preliminary guidance only; the responsible passport "
            "office makes the final decision. Never add requirements not present in the facts.\n\n"
            f"FULL CASE FACTS:\n{facts_json}"
        ),
        expected_output=(
            "A bilingual Markdown Passport Readiness Report with valid tables, exact figures, "
            "custom checklist, visible flags, sources, and disclaimer."
        ),
        agent=document_architect,
        context=[policy_task, fee_task],
    )

    crew = Crew(
        agents=[policy_guardian, fee_calculator, document_architect],
        tasks=[policy_task, fee_task, report_task],
        process=Process.sequential,
        verbose=True,
        memory=False,
    )
    result = await crew.kickoff_async()
    return getattr(result, "raw", str(result))

