from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Profession(str, Enum):
    PRIVATE_EMPLOYEE = "private_employee"
    GOVERNMENT_EMPLOYEE = "government_employee"
    RETIRED_GOVERNMENT = "retired_government"
    STUDENT = "student"
    BUSINESS = "business"
    OTHER = "other"


class DeliverySpeed(str, Enum):
    REGULAR = "regular"
    EXPRESS = "express"
    SUPER_EXPRESS = "super_express"


class ApplicantProfile(BaseModel):
    """Validated, non-sensitive inputs needed for a readiness assessment."""

    age: int = Field(ge=0, le=120)
    profession: Profession
    urgency_days: int | None = Field(default=None, ge=1, le=365)
    requested_validity_years: Literal[5, 10] | None = None
    page_count: Literal[48, 64] = 48
    delivery_speed: DeliverySpeed | None = None
    has_nid: bool = False
    has_english_brc: bool = False
    has_go_noc: bool = False
    location: str = "Bangladesh"
    application_type: Literal["new", "reissue"] = "new"
    payment_method: Literal["online", "offline"] = "online"
    name_or_marital_change: bool = False
    other_personal_data_change: bool = False
    lost_passport: bool = False


class EligibilityDecision(BaseModel):
    permitted_validity_years: list[int]
    selected_validity_years: int
    permitted_page_counts: list[int]
    selected_page_count: int
    identification_requirement_en: str
    identification_requirement_bn: str
    conflicts_en: list[str] = Field(default_factory=list)
    conflicts_bn: list[str] = Field(default_factory=list)
    advisories_en: list[str] = Field(default_factory=list)
    advisories_bn: list[str] = Field(default_factory=list)


class FeeDecision(BaseModel):
    requested_delivery: DeliverySpeed
    charged_delivery_tier: DeliverySpeed
    delivery_time: str
    delivery_time_bn: str
    base_fee_bdt: int
    vat_rate: str = "15%"
    vat_bdt: int
    total_fee_bdt: int
    benefit_note: str | None = None
    benefit_note_bn: str | None = None


class DocumentItem(BaseModel):
    en: str
    bn: str


class ReadinessFacts(BaseModel):
    profile: ApplicantProfile
    eligibility: EligibilityDecision
    fee: FeeDecision
    documents: list[DocumentItem]
    warnings_en: list[str]
    warnings_bn: list[str]
    data_source: str
    data_version: str
    source_urls: list[str]
