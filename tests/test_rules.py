from __future__ import annotations

import pytest

from amar_passport.models import ApplicantProfile, DeliverySpeed, Profession
from amar_passport.repository import PassportKnowledgeBase
from amar_passport.rules import determine_eligibility, evaluate_profile


@pytest.fixture
def knowledge():
    return PassportKnowledgeBase().load(prefer_remote=False)[0]


def test_minor_request_is_flagged_and_corrected(knowledge):
    profile = ApplicantProfile(
        age=15,
        profession=Profession.STUDENT,
        urgency_days=30,
        requested_validity_years=10,
        page_count=64,
        has_english_brc=True,
    )
    facts = evaluate_profile(profile, knowledge, "test")

    assert facts.eligibility.selected_validity_years == 5
    assert facts.eligibility.selected_page_count == 48
    assert len(facts.eligibility.conflicts_en) == 2
    assert all("INCONSISTENCY" in item for item in facts.eligibility.conflicts_en)
    assert facts.fee.total_fee_bdt == 4025


def test_assignment_example_gets_express_64_page_10_year_fee(knowledge):
    profile = ApplicantProfile(
        age=24,
        profession=Profession.PRIVATE_EMPLOYEE,
        urgency_days=14,
        requested_validity_years=10,
        page_count=64,
        has_nid=True,
        payment_method="offline",
    )
    facts = evaluate_profile(profile, knowledge, "test")

    assert facts.fee.requested_delivery == DeliverySpeed.EXPRESS
    assert facts.fee.base_fee_bdt == 9000
    assert facts.fee.vat_bdt == 1350
    assert facts.fee.total_fee_bdt == 10350
    assert any("Profession proof" in doc.en for doc in facts.documents)
    assert any("Payment slip" in doc.en for doc in facts.documents)


def test_current_policy_allows_ten_year_validity_over_65():
    profile = ApplicantProfile(
        age=70,
        profession=Profession.OTHER,
        requested_validity_years=10,
        has_nid=True,
    )
    decision = determine_eligibility(profile)

    assert decision.selected_validity_years == 10
    assert decision.permitted_validity_years == [5, 10]
    assert "cancelled" in decision.advisories_en[0]


@pytest.mark.parametrize(
    ("age", "expected_fragment"),
    [(17, "Birth Registration"), (18, "NID or English"), (20, "NID or English"), (21, "mandatory")],
)
def test_identification_age_boundaries(age, expected_fragment):
    profile = ApplicantProfile(age=age, profession=Profession.OTHER)
    assert expected_fragment in determine_eligibility(profile).identification_requirement_en


def test_government_noc_applies_official_fee_benefit(knowledge):
    profile = ApplicantProfile(
        age=35,
        profession=Profession.GOVERNMENT_EMPLOYEE,
        delivery_speed=DeliverySpeed.EXPRESS,
        requested_validity_years=10,
        page_count=48,
        has_nid=True,
        has_go_noc=True,
    )
    facts = evaluate_profile(profile, knowledge, "test")

    assert facts.fee.charged_delivery_tier == DeliverySpeed.REGULAR
    assert facts.fee.total_fee_bdt == 5750
    assert facts.fee.benefit_note is not None

