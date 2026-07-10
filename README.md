# 🛂 Amar Passport — Virtual Consular Officer

A **Multi-Agent System (MAS)** built with [CrewAI](https://github.com/crewAIInc/crewAI) that acts as a "Virtual Consular Officer" for the Bangladesh E-Passport Portal.

Given a user's profile (Age, Profession, Urgency), the system produces a comprehensive **Passport Readiness Report** in both **English** and **Bangla (বাংলা)**.

---

## 🤖 The Crew — Three Specialized Agents

| Agent | Role | Responsibility |
|---|---|---|
| **The Policy Guardian** | Bangladesh Passport Policy Expert | Determines permitted validity (5 vs 10 years), page count (48 vs 64), and required identification (NID vs BRC) based on the applicant's age. Flags inconsistencies (e.g. a 15-year-old requesting 10 years). |
| **The Chancellor of the Exchequer** | Financial Auditor | Calculates the exact BDT fee including 15% VAT based on page count, delivery speed, and validity. Applies NOC-based government employee benefits. |
| **The Document Architect** | Documentation Officer | Generates a customized bilingual checklist — GO/NOC for govt employees, Marriage Certificate for name changes, Parent's NID for minors, etc. |

---

## 🏗️ Architecture

```
┌─────────────────────────────┐
│  cli.py (Entry Point)       │
│  --profile / --demo / ...   │
└────────────┬────────────────┘
             │
     ┌───────▼────────┐
     │  repository.py  │  ← Scrapes official portal → Falls back to local JSON
     └───────┬────────┘
             │  knowledge + data_source
     ┌───────▼────────┐
     │   rules.py      │  ← Deterministic policy engine (eligibility, fees, docs)
     └───────┬────────┘
             │  ReadinessFacts
     ┌───────▼────────┐
     │   crew.py       │  ← 3-agent CrewAI sequential pipeline (online mode)
     │   report.py     │  ← Deterministic Markdown renderer (offline / fallback)
     └────────────────┘
```

**Key design decision**: The rules engine (`rules.py`) computes all deterministic policy facts *before* passing them to the LLM agents. The agents audit, explain, and format — they never override policy.

---

## ⚡ Quick Start

### 1. Install

```bash
# Clone and install (editable mode)
pip install -e ".[dev]"
```

### 2. Configure (for online/CrewAI mode)

```bash
cp .env.example .env
# Edit .env with your API key:
#   MODEL=openai/gpt-4o-mini
#   OPENAI_API_KEY=sk-...
```

### 3. Run

```bash
# ── Offline mode (no API key needed, uses deterministic renderer) ──
amar-passport --demo adult --offline

# ── Online mode (uses CrewAI agents with verbose=True) ──
amar-passport --demo adult

# ── Custom profile ──
amar-passport --profile examples/adult_private.json --output reports/report.md

# ── Minor with intentional inconsistency (flags 10-year + 64-page request) ──
amar-passport --demo minor --offline
```

You can also run it as a module:
```bash
python -m amar_passport --demo adult --offline
```

---

## 📝 Example Input

```json
{
  "age": 24,
  "profession": "private_employee",
  "urgency_days": 14,
  "requested_validity_years": 10,
  "page_count": 64,
  "has_nid": true,
  "location": "Dhaka",
  "application_type": "new",
  "payment_method": "offline"
}
```

**Expected output** (offline mode):

| Category | Recommendation |
|---|---|
| Eligibility | Permitted validity: 5, 10 year(s); permitted pages: 48, 64 |
| Recommended passport | **64 pages, 10 years** |
| Identification | NID is mandatory for applications submitted inside Bangladesh |
| Delivery type | **Express** (7 working days / 10 calendar days) |
| Fee before VAT | BDT 9,000 |
| VAT | BDT 1,350 (15%) |
| Total fee (VAT included) | **BDT 10,350** |
| Documents needed | Application form, Application summary, Payment slip, NID, Profession proof |

---

## 💰 2026 Official Fee Structure (VAT inclusive)

| Pages | Validity | Regular | Express | Super Express |
|---|---|---|---|---|
| 48 | 5 years | ৳ 4,025 | ৳ 6,325 | ৳ 8,625 |
| 48 | 10 years | ৳ 5,750 | ৳ 8,050 | ৳ 10,350 |
| 64 | 5 years | ৳ 6,325 | ৳ 8,625 | ৳ 12,075 |
| 64 | 10 years | ৳ 8,050 | ৳ 10,350 | ৳ 13,800 |

---

## 🛡️ Error Handling & Fallbacks

| Scenario | Behaviour |
|---|---|
| 15-year-old requests 10-year passport | Flagged as `INCONSISTENCY`, corrected to 5 years |
| Minor requests 64 pages | Flagged as `INCONSISTENCY`, corrected to 48 pages |
| Official portal is unreachable | Falls back to `data/passport_rules_2026.json` (local database) |
| CrewAI / LLM fails at runtime | Falls back to the deterministic `report.py` renderer |
| Missing NID for adult applicant | Flagged as `MISSING` warning |
| Lost passport marked as "new" | Flagged as `CHECK INPUT` warning |

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=amar_passport --cov-report=term-missing
```

---

## 📂 Project Structure

```
Amar Passport/
├── data/
│   └── passport_rules_2026.json   # Versioned local policy database
├── examples/
│   ├── adult_private.json         # 24-year-old private employee
│   └── minor_inconsistent.json    # 15-year-old requesting 10yr + 64pg
├── reports/                       # Generated reports go here
├── src/amar_passport/
│   ├── __init__.py
│   ├── __main__.py                # python -m amar_passport
│   ├── cli.py                     # CLI argument parsing + orchestration
│   ├── crew.py                    # CrewAI 3-agent sequential pipeline
│   ├── models.py                  # Pydantic data models
│   ├── report.py                  # Deterministic Markdown renderer
│   ├── repository.py              # Official scraper + local fallback
│   └── rules.py                   # Deterministic policy/fee/doc engine
├── tests/
│   ├── conftest.py
│   ├── test_report.py
│   ├── test_repository.py
│   └── test_rules.py
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 📜 License

MIT
