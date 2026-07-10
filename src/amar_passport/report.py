from __future__ import annotations

from amar_passport.models import ReadinessFacts


def render_markdown(facts: ReadinessFacts) -> str:
    """Render a deterministic bilingual report for offline and fallback operation."""

    e = facts.eligibility
    f = facts.fee
    docs_en = "<br>".join(f"{index}. {item.en}" for index, item in enumerate(facts.documents, 1))
    docs_bn = "<br>".join(f"{index}. {item.bn}" for index, item in enumerate(facts.documents, 1))
    warning_en = "<br>".join(facts.warnings_en) if facts.warnings_en else "No inconsistency detected"
    warning_bn = (
        "<br>".join(facts.warnings_bn)
        if facts.warnings_bn
        else "কোনো অসঙ্গতি পাওয়া যায়নি"
    )
    benefit_en = f.benefit_note or "Not applicable"
    benefit_bn = f.benefit_note_bn or "প্রযোজ্য নয়"

    lines = [
        "# Amar Passport — Passport Readiness Report",
        "",
        "> Preliminary guidance only. The responsible passport office makes the final decision.",
        "",
        "## English",
        "",
        "| Category | Recommendation |",
        "|---|---|",
        f"| Eligibility | Permitted validity: {', '.join(map(str, e.permitted_validity_years))} year(s); permitted pages: {', '.join(map(str, e.permitted_page_counts))} |",
        f"| Recommended passport | **{e.selected_page_count} pages, {e.selected_validity_years} years** |",
        f"| Identification | {e.identification_requirement_en} |",
        f"| Delivery type | **{f.requested_delivery.value.replace('_', ' ').title()}** ({f.delivery_time}) |",
        f"| Fee before VAT | BDT {f.base_fee_bdt:,} |",
        f"| VAT | BDT {f.vat_bdt:,} (15%) |",
        f"| Total fee (VAT included) | **BDT {f.total_fee_bdt:,}** |",
        f"| Government service benefit | {benefit_en} |",
        f"| Documents needed | {docs_en} |",
        f"| Flags | {warning_en} |",
        "",
        "## বাংলা",
        "",
        "| বিষয় | সুপারিশ |",
        "|---|---|",
        f"| যোগ্যতা | অনুমোদিত মেয়াদ: {', '.join(map(str, e.permitted_validity_years))} বছর; অনুমোদিত পৃষ্ঠা: {', '.join(map(str, e.permitted_page_counts))} |",
        f"| সুপারিশকৃত পাসপোর্ট | **{e.selected_page_count} পৃষ্ঠা, {e.selected_validity_years} বছর** |",
        f"| পরিচয়পত্র | {e.identification_requirement_bn} |",
        f"| ডেলিভারির ধরন | **{_delivery_bn(f.requested_delivery.value)}** ({f.delivery_time_bn}) |",
        f"| ভ্যাট-পূর্ব ফি | {f.base_fee_bdt:,} টাকা |",
        f"| ভ্যাট | {f.vat_bdt:,} টাকা (১৫%) |",
        f"| মোট ফি (ভ্যাটসহ) | **{f.total_fee_bdt:,} টাকা** |",
        f"| সরকারি চাকরির সুবিধা | {benefit_bn} |",
        f"| প্রয়োজনীয় কাগজপত্র | {docs_bn} |",
        f"| সতর্কতা | {warning_bn} |",
        "",
        "## Audit trail",
        "",
        f"- Data source: `{facts.data_source}`",
        f"- Local policy version: `{facts.data_version}`",
        "- Official references:",
        *[f"  - {url}" for url in facts.source_urls],
    ]
    if e.advisories_en:
        lines.extend(["- Policy notes:", *[f"  - {note}" for note in e.advisories_en]])
    if e.advisories_bn:
        lines.extend(["- নীতি নোট:", *[f"  - {note}" for note in e.advisories_bn]])
    return "\n".join(lines) + "\n"


def _delivery_bn(delivery: str) -> str:
    return {
        "regular": "রেগুলার",
        "express": "এক্সপ্রেস",
        "super_express": "সুপার এক্সপ্রেস",
    }[delivery]

