from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from amar_passport.models import (
    ApplicantProfile,
    DeliverySpeed,
    DocumentItem,
    EligibilityDecision,
    FeeDecision,
    Profession,
    ReadinessFacts,
)


def evaluate_profile(
    profile: ApplicantProfile, knowledge: dict[str, Any], data_source: str
) -> ReadinessFacts:
    eligibility = determine_eligibility(profile)
    fee = calculate_fee(profile, eligibility, knowledge)
    documents = build_checklist(profile, eligibility, knowledge)

    warnings_en = [*eligibility.conflicts_en]
    warnings_bn = [*eligibility.conflicts_bn]
    missing_en, missing_bn = _missing_document_warnings(profile)
    warnings_en.extend(missing_en)
    warnings_bn.extend(missing_bn)

    metadata = knowledge["metadata"]
    return ReadinessFacts(
        profile=profile,
        eligibility=eligibility,
        fee=fee,
        documents=documents,
        warnings_en=warnings_en,
        warnings_bn=warnings_bn,
        data_source=data_source,
        data_version=metadata["version"],
        source_urls=[
            metadata["official_fee_url"],
            metadata["official_instruction_url"],
            metadata["official_documents_url"],
        ],
    )


def determine_eligibility(profile: ApplicantProfile) -> EligibilityDecision:
    conflicts_en: list[str] = []
    conflicts_bn: list[str] = []
    advisories_en: list[str] = []
    advisories_bn: list[str] = []

    if profile.age < 18:
        permitted_validities = [5]
        permitted_pages = [48]
        selected_validity = 5
        selected_pages = 48
        id_en = "English online Birth Registration Certificate; parent NID number is required"
        id_bn = "ইংরেজি অনলাইন জন্মনিবন্ধন সনদ; পিতা বা মাতার NID নম্বর আবশ্যক"
        if profile.requested_validity_years == 10:
            conflicts_en.append(
                "INCONSISTENCY: An applicant under 18 cannot receive 10-year validity; "
                "the recommendation was corrected to 5 years."
            )
            conflicts_bn.append(
                "অসঙ্গতি: ১৮ বছরের কম বয়সী আবেদনকারী ১০ বছরের মেয়াদ পেতে পারেন না; "
                "সুপারিশ ৫ বছরে সংশোধন করা হয়েছে।"
            )
        if profile.page_count == 64:
            conflicts_en.append(
                "INCONSISTENCY: An applicant under 18 is limited to 48 pages; "
                "the recommendation was corrected to 48 pages."
            )
            conflicts_bn.append(
                "অসঙ্গতি: ১৮ বছরের কম বয়সী আবেদনকারী সর্বোচ্চ ৪৮ পৃষ্ঠা পেতে পারেন; "
                "সুপারিশ ৪৮ পৃষ্ঠায় সংশোধন করা হয়েছে।"
            )
    else:
        permitted_validities = [5, 10]
        permitted_pages = [48, 64]
        selected_validity = profile.requested_validity_years or 10
        selected_pages = profile.page_count
        if profile.age <= 20:
            id_en = "NID or English online Birth Registration Certificate"
            id_bn = "NID অথবা ইংরেজি অনলাইন জন্মনিবন্ধন সনদ"
        else:
            id_en = "NID is mandatory for applications submitted inside Bangladesh"
            id_bn = "বাংলাদেশের ভেতরে আবেদন করলে NID আবশ্যক"

    if profile.age >= 65:
        advisories_en.append(
            "Current 2026 official instructions allow 5- or 10-year validity for applicants "
            "aged 65+; the former five-year-only restriction has been cancelled."
        )
        advisories_bn.append(
            "২০২৬ সালের বর্তমান নির্দেশনা অনুযায়ী ৬৫+ বয়সী আবেদনকারীদের ৫ বা ১০ বছরের "
            "মেয়াদ অনুমোদিত; পূর্বের শুধু-৫-বছর বিধিনিষেধ বাতিল করা হয়েছে।"
        )

    return EligibilityDecision(
        permitted_validity_years=permitted_validities,
        selected_validity_years=selected_validity,
        permitted_page_counts=permitted_pages,
        selected_page_count=selected_pages,
        identification_requirement_en=id_en,
        identification_requirement_bn=id_bn,
        conflicts_en=conflicts_en,
        conflicts_bn=conflicts_bn,
        advisories_en=advisories_en,
        advisories_bn=advisories_bn,
    )


def recommend_delivery(profile: ApplicantProfile) -> DeliverySpeed:
    if profile.delivery_speed is not None:
        return profile.delivery_speed
    if profile.urgency_days is None or profile.urgency_days > 21:
        return DeliverySpeed.REGULAR
    if profile.urgency_days <= 3:
        return DeliverySpeed.SUPER_EXPRESS
    return DeliverySpeed.EXPRESS


_DELIVERY_BN = {
    "regular": "রেগুলার",
    "express": "এক্সপ্রেস",
    "super_express": "সুপার এক্সপ্রেস",
}

_DELIVERY_DAYS_BN = {
    "regular": "১৫ কার্যদিবস / ২১ ক্যালেন্ডার দিন",
    "express": "৭ কার্যদিবস / ১০ ক্যালেন্ডার দিন",
    "super_express": "২ কার্যদিবস",
}


def calculate_fee(
    profile: ApplicantProfile,
    eligibility: EligibilityDecision,
    knowledge: dict[str, Any],
) -> FeeDecision:
    requested_delivery = recommend_delivery(profile)
    charged_tier = requested_delivery
    benefit_note = None
    benefit_note_bn = None

    if profile.profession == Profession.GOVERNMENT_EMPLOYEE and profile.has_go_noc:
        if requested_delivery == DeliverySpeed.EXPRESS:
            charged_tier = DeliverySpeed.REGULAR
            benefit_note = "Valid NOC: Express service is charged at the Regular fee."
            benefit_note_bn = "বৈধ NOC: এক্সপ্রেস সেবা রেগুলার ফি-তে চার্জ করা হয়েছে।"
        elif requested_delivery == DeliverySpeed.SUPER_EXPRESS:
            charged_tier = DeliverySpeed.EXPRESS
            benefit_note = "Valid NOC: Super Express service is charged at the Express fee."
            benefit_note_bn = "বৈধ NOC: সুপার এক্সপ্রেস সেবা এক্সপ্রেস ফি-তে চার্জ করা হয়েছে।"

    total = knowledge["fees_2026"][f"{eligibility.selected_page_count}_pages"][
        f"{eligibility.selected_validity_years}_years"
    ][charged_tier.value]
    vat_rate = Decimal(str(knowledge["metadata"]["vat_rate"]))
    base = int(
        (Decimal(total) / (Decimal("1") + vat_rate)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )

    return FeeDecision(
        requested_delivery=requested_delivery,
        charged_delivery_tier=charged_tier,
        delivery_time=knowledge["delivery_days"][requested_delivery.value],
        delivery_time_bn=_DELIVERY_DAYS_BN[requested_delivery.value],
        base_fee_bdt=base,
        vat_bdt=total - base,
        total_fee_bdt=total,
        benefit_note=benefit_note,
        benefit_note_bn=benefit_note_bn,
    )


def build_checklist(
    profile: ApplicantProfile,
    eligibility: EligibilityDecision,
    knowledge: dict[str, Any],
) -> list[DocumentItem]:
    docs = knowledge["required_docs"]
    keys = ["application_form", "application_summary"]
    if profile.payment_method == "offline":
        keys.append("payment_slip")

    if profile.age < 18:
        keys.extend(["brc", "parents_nid"])
        if profile.age < 6:
            keys.append("child_photo")
    elif profile.age <= 20:
        keys.append("nid" if profile.has_nid else "brc")
    else:
        keys.append("nid")

    if profile.profession == Profession.GOVERNMENT_EMPLOYEE:
        keys.append("government_noc")
    elif profile.profession == Profession.RETIRED_GOVERNMENT:
        keys.extend(["prl_order", "previous_passport"])
    elif profile.profession in {
        Profession.PRIVATE_EMPLOYEE,
        Profession.STUDENT,
        Profession.BUSINESS,
    }:
        keys.append("profession_proof")

    if profile.name_or_marital_change:
        keys.extend(["marriage_certificate", "change_support"])
    elif profile.other_personal_data_change:
        keys.append("change_support")

    if profile.application_type == "reissue":
        keys.append("previous_passport")
    if profile.lost_passport:
        keys.append("police_report")

    # Keep the first occurrence while preserving a human-friendly order.
    unique_keys = list(dict.fromkeys(keys))
    return [DocumentItem(**docs[key]) for key in unique_keys]


def _missing_document_warnings(
    profile: ApplicantProfile,
) -> tuple[list[str], list[str]]:
    warnings_en: list[str] = []
    warnings_bn: list[str] = []
    if profile.age < 18 and not profile.has_english_brc:
        warnings_en.append("MISSING: English online Birth Registration Certificate is required.")
        warnings_bn.append("অনুপস্থিত: ইংরেজি অনলাইন জন্মনিবন্ধন সনদ আবশ্যক।")
    elif 18 <= profile.age <= 20 and not (profile.has_nid or profile.has_english_brc):
        warnings_en.append("MISSING: Provide an NID or English online Birth Registration Certificate.")
        warnings_bn.append("অনুপস্থিত: NID অথবা ইংরেজি অনলাইন জন্মনিবন্ধন সনদ প্রদান করুন।")
    elif profile.age > 20 and not profile.has_nid:
        warnings_en.append("MISSING: NID is mandatory for an application inside Bangladesh.")
        warnings_bn.append("অনুপস্থিত: বাংলাদেশের ভেতরে আবেদনের জন্য NID আবশ্যক।")
    if profile.lost_passport and profile.application_type != "reissue":
        warnings_en.append("CHECK INPUT: A lost-passport case should normally be submitted as a reissue.")
        warnings_bn.append("ইনপুট যাচাই: হারানো পাসপোর্টের ক্ষেত্রে সাধারণত পুনঃইস্যু হিসেবে আবেদন করা উচিত।")
    return warnings_en, warnings_bn

