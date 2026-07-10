from __future__ import annotations

from amar_passport.models import ApplicantProfile, Profession
from amar_passport.report import render_markdown
from amar_passport.repository import PassportKnowledgeBase
from amar_passport.rules import evaluate_profile


def test_report_is_bilingual_markdown_with_audit_trail():
    knowledge, source = PassportKnowledgeBase().load(prefer_remote=False)
    facts = evaluate_profile(
        ApplicantProfile(age=24, profession=Profession.PRIVATE_EMPLOYEE, has_nid=True),
        knowledge,
        source,
    )
    report = render_markdown(facts)

    assert "| Category | Recommendation |" in report
    assert "| বিষয় | সুপারিশ |" in report
    assert "Total fee (VAT included)" in report
    assert "মোট ফি (ভ্যাটসহ)" in report
    assert "## Audit trail" in report

