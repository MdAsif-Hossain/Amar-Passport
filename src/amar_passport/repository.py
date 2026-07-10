from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "passport_rules_2026.json"


class KnowledgeBaseError(RuntimeError):
    """Raised when neither official nor local policy data can be loaded."""


class PassportKnowledgeBase:
    """Loads official fee data and falls back to the versioned local database."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path

    def load(self, prefer_remote: bool = True) -> tuple[dict[str, Any], str]:
        local = self._load_local()
        if not prefer_remote:
            return local, "local_database (remote refresh disabled)"

        try:
            remote_fees = self._scrape_official_fees(
                local["metadata"]["official_fee_url"]
            )
            refreshed = copy.deepcopy(local)
            refreshed["fees_2026"] = remote_fees
            return refreshed, "live_official_portal"
        except Exception as exc:  # The local copy is the deliberate resilience boundary.
            reason = f"{type(exc).__name__}: {str(exc)[:120]}"
            return local, f"local_fallback ({reason})"

    def _load_local(self) -> dict[str, Any]:
        try:
            with self.db_path.open("r", encoding="utf-8") as handle:
                data: dict[str, Any] = json.load(handle)
            self._validate_fee_table(data["fees_2026"])
            return data
        except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
            raise KnowledgeBaseError(f"Cannot load local policy database: {exc}") from exc

    def _scrape_official_fees(self, url: str) -> dict[str, Any]:
        response = requests.get(
            url,
            timeout=(3.05, 10),
            headers={"User-Agent": "AmarPassport/1.0 educational-policy-checker"},
        )
        response.raise_for_status()
        text = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)

        fees: dict[str, Any] = {}
        for pages in (48, 64):
            page_key = f"{pages}_pages"
            fees[page_key] = {}
            for years in (5, 10):
                year_key = f"{years}_years"
                section_pattern = re.compile(
                    rf"{pages}\s+pages\s+and\s+{years}\s+years\s+validity"
                    rf"(?P<section>.*?)(?=e-?Passport\s+with\s+(?:48|64)\s+pages|$)",
                    re.IGNORECASE | re.DOTALL,
                )
                section_match = section_pattern.search(text)
                if not section_match:
                    raise ValueError(f"Official page is missing the {pages}/{years} fee section")

                section = section_match.group("section")
                fees[page_key][year_key] = {}
                labels = {
                    "regular": "Regular",
                    "express": "Express",
                    "super_express": r"Super[\s-]*Express",
                }
                for key, label in labels.items():
                    amount_match = re.search(
                        rf"{label}\s+delivery\s*:\s*(?:TK|BDT|৳)\s*([\d,]+)",
                        section,
                        re.IGNORECASE,
                    )
                    if not amount_match:
                        raise ValueError(f"Official page is missing {key} for {pages}/{years}")
                    fees[page_key][year_key][key] = int(
                        amount_match.group(1).replace(",", "")
                    )

        self._validate_fee_table(fees)
        return fees

    @staticmethod
    def _validate_fee_table(fees: dict[str, Any]) -> None:
        for pages in (48, 64):
            for years in (5, 10):
                for delivery in ("regular", "express", "super_express"):
                    value = fees[f"{pages}_pages"][f"{years}_years"][delivery]
                    if not isinstance(value, int) or value <= 0:
                        raise ValueError(
                            f"Invalid fee for {pages} pages/{years} years/{delivery}"
                        )

