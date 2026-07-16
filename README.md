<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/CrewAI-Multi--Agent-ff6b35?style=for-the-badge" alt="CrewAI" />
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Pydantic-v2-e92063?style=for-the-badge&logo=pydantic&logoColor=white" alt="Pydantic" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License" />
</p>

<h1 align="center">🛂 Amar Passport</h1>
<h3 align="center">AI-Powered Virtual Consular Officer for Bangladesh e-Passport</h3>

<p align="center">
  A production-grade <strong>Multi-Agent System</strong> built with CrewAI that automates passport readiness assessment — determining eligibility, calculating fees with 15% VAT, and generating personalized bilingual document checklists.
</p>

---

## 🎬 Live Demo

https://github.com/user-attachments/assets/3096e1bb-1b3c-44a6-b080-88ce7a39323e

---

## 💡 The Problem

Navigating the Bangladesh E-Passport Portal is overwhelming. Rules vary by age, profession, and delivery type. Applicants frequently:
- Request invalid configurations (e.g., a 15-year-old asking for a 10-year passport)
- Miscalculate fees by forgetting 15% VAT or missing NOC-based discounts
- Submit incomplete documents, causing rejections and wasted trips

**Amar Passport solves this** by deploying three specialized AI agents that collaboratively audit, calculate, and compile a complete readiness report — catching every inconsistency before the applicant reaches the passport office.

---

## 🤖 The Crew — Three Specialized Agents

```
User Profile ──▶ 🛡️ Policy Guardian ──▶ 💰 Chancellor ──▶ 📋 Document Architect ──▶ Report
                      │                       │                        │
                      ▼                       ▼                        ▼
                 Age eligibility         Fee + 15% VAT          Bilingual checklist
                 Validity (5/10yr)       Delivery tier           Profession-specific docs
                 Page count (48/64)      NOC benefits            Inconsistency flags
```

| Agent | Role | What It Does |
|:------|:-----|:-------------|
| 🛡️ **The Policy Guardian** | Eligibility Expert | Validates age-based restrictions (under 18 → 5yr/48pg only), NID vs BRC requirements, and flags inconsistent requests |
| 💰 **The Chancellor of the Exchequer** | Financial Auditor | Computes exact BDT fee from the 2026 fee structure, decomposes base + 15% VAT, and applies NOC-based government employee discounts |
| 📋 **The Document Architect** | Documentation Officer | Builds a personalized bilingual (English + বাংলা) document checklist — GO/NOC for govt employees, Marriage Certificate for name changes, Parent's NID for minors |

> **Key Design Decision:** A deterministic rules engine ([`rules.py`](src/amar_passport/rules.py)) computes all policy facts *before* passing them to the LLM agents. The agents audit, explain, and format — they never override policy. This guarantees correctness even if the LLM hallucinates.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────┐
│  CLI / Web UI (Entry Points)    │
│  cli.py  ·  web.py + FastAPI    │
└──────────────┬──────────────────┘
               │
       ┌───────▼─────────┐
       │  repository.py   │  ← Scrapes official portal → Falls back to local JSON
       └───────┬─────────┘
               │  knowledge + data_source
       ┌───────▼─────────┐
       │   rules.py       │  ← Deterministic policy engine (eligibility, fees, docs)
       └───────┬─────────┘
               │  ReadinessFacts (Pydantic model)
       ┌───────▼─────────┐
       │   crew.py        │  ← 3-agent CrewAI sequential pipeline (online mode)
       │   report.py      │  ← Deterministic Markdown renderer (offline / fallback)
       └─────────────────┘
```

### Technical Highlights

- **Dual-mode operation:** Online (CrewAI + LLM) with automatic fallback to offline deterministic rendering
- **Live data refresh:** Scrapes the official [epassport.gov.bd](https://www.epassport.gov.bd) fee page; gracefully falls back to a versioned local database if the portal is unreachable
- **Strict validation:** Pydantic v2 models enforce input constraints at the boundary (`age: 0-120`, `page_count: 48|64`, `validity: 5|10`)
- **Task delegation:** Fee Calculator receives Policy Guardian's output as `context`, ensuring the fee is always computed against the *corrected* (not the *requested*) passport configuration
- **Bilingual output:** Full English + Bangla (বাংলা) tables with proper font rendering

---

## ⚡ Quick Start

### 1. Install

```bash
git clone https://github.com/MdAsif-Hossain/Amar-Passport.git
cd Amar-Passport
pip install -e ".[dev]"
```

### 2. Configure (for online/CrewAI mode)

```bash
cp .env.example .env
# Edit .env with your API key:
#   MODEL=groq/llama-3.3-70b-versatile
#   GROQ_API_KEY=gsk_...
```

### 3. Run

```bash
# ── Offline mode (no API key needed) ──
amar-passport --demo adult --offline

# ── Online mode (CrewAI agents with verbose=True) ──
amar-passport --demo adult

# ── Custom profile ──
amar-passport --profile examples/adult_private.json --output reports/report.md

# ── Web UI ──
amar-passport-web
# Then open http://localhost:8000
```

---

## 📝 Example Scenario

**Input:** *"I am a 24-year-old private sector employee. I need a 64-page passport urgently because I have a business trip in two weeks. I have an NID and I live in Dhaka."*

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

**Output:**

| Category | Recommendation |
|:---------|:---------------|
| Eligibility | Permitted validity: 5, 10 years; permitted pages: 48, 64 |
| Recommended passport | **64 pages, 10 years** |
| Identification | NID is mandatory for applications submitted inside Bangladesh |
| Delivery type | **Express** (7 working days / 10 calendar days) |
| Fee before VAT | BDT 9,000 |
| VAT (15%) | BDT 1,350 |
| **Total fee** | **BDT 10,350** |
| Documents needed | Application form, Application summary, Payment slip, NID, Profession proof |

---

## 🛡️ Error Handling & Resilience

| Scenario | System Behaviour |
|:---------|:-----------------|
| 15-year-old requests 10-year passport | `INCONSISTENCY` flagged → auto-corrected to 5 years |
| Minor requests 64 pages | `INCONSISTENCY` flagged → auto-corrected to 48 pages |
| Official portal unreachable | Falls back to versioned `data/passport_rules_2026.json` |
| CrewAI / LLM fails at runtime | Falls back to deterministic `report.py` renderer |
| Missing NID for adult applicant | `MISSING` warning raised in the report |
| Lost passport marked as "new" | `CHECK INPUT` warning raised |

---

## 💰 2026 Official Fee Structure (VAT-inclusive)

| Pages | Validity | Regular | Express | Super Express |
|:------|:---------|--------:|--------:|--------------:|
| 48 | 5 years | ৳ 4,025 | ৳ 6,325 | ৳ 8,625 |
| 48 | 10 years | ৳ 5,750 | ৳ 8,050 | ৳ 10,350 |
| 64 | 5 years | ৳ 6,325 | ৳ 8,625 | ৳ 12,075 |
| 64 | 10 years | ৳ 8,050 | ৳ 10,350 | ৳ 13,800 |

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
Amar-Passport/
├── data/
│   └── passport_rules_2026.json     # Versioned local policy database (fallback)
├── examples/
│   ├── adult_private.json           # 24-year-old private employee
│   └── minor_inconsistent.json      # 15-year-old requesting 10yr + 64pg (flags errors)
├── reports/                         # Generated Markdown reports
├── src/amar_passport/
│   ├── __init__.py
│   ├── __main__.py                  # python -m amar_passport
│   ├── cli.py                       # CLI argument parsing + orchestration
│   ├── crew.py                      # CrewAI 3-agent sequential pipeline
│   ├── models.py                    # Pydantic v2 data models
│   ├── report.py                    # Deterministic Markdown renderer (offline)
│   ├── repository.py                # Official portal scraper + local fallback
│   ├── rules.py                     # Deterministic policy / fee / document engine
│   ├── web.py                       # FastAPI web server
│   └── static/
│       └── index.html               # Glassmorphism web UI
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

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|:------|:-----------|:--------|
| AI Orchestration | **CrewAI** | Multi-agent sequential pipeline with task delegation |
| LLM Backend | **Groq / Gemini / OpenAI** (via LiteLLM) | Natural language reasoning and report generation |
| Web Framework | **FastAPI** | REST API with async request handling |
| Data Validation | **Pydantic v2** | Strict input/output schemas with type safety |
| Web Scraping | **BeautifulSoup4** + Requests | Official portal fee extraction |
| Frontend | **Vanilla JS** + CSS (Glassmorphism) | Dark-mode UI with Inter typography, no framework dependencies |
| Testing | **pytest** | Unit tests for rules, reports, and repository |

---

## 📜 License

MIT — see [LICENSE](LICENSE) for details.
