# Procurement Agent System

A multi-agent system built with [AutoGen](https://github.com/microsoft/autogen) that automates the core backend workflows of an accounts-payable / procurement function — invoice processing, 3-way matching, payment release, exception handling, and vendor communication.

Built during an undergraduate internship at EY as a proof-of-concept for how drag-and-drop agent orchestration platforms (think UiPath, SAP, or custom low-code tools) can be backed by an LLM-driven agent layer.

---

## What it does

The system runs as a group chat where a **GroupChatManager** routes each user instruction to the most appropriate specialist agent.  Each agent owns exactly one responsibility, queries a local SQLite database, and hands off to the next agent if needed.

| Agent | Responsibility |
|---|---|
| `InvoiceAgent` | Parses invoice details and persists them via LLM-generated SQL |
| `MatcherAgent` | 3-way quantity match across PO → GR → Invoice |
| `ExceptionHandlerAgent` | Logs mismatches and missing-data errors to the exceptions table |
| `PaymentProcessingAgent` | Releases payment once a Matched status is confirmed |
| `StatusAgent` | Looks up payment + match status for any invoice |
| `VendorCommunicationAgent` | Drafts a vendor-facing status update from live DB data |
| `ReportingAgent` | Runs canned SQL reports (billed per vendor, overdue, open exceptions) |

---

## Architecture

```
User instruction
      │
      ▼
GroupChatManager  (AutoGen, speaker_selection="auto")
      │
      ├─► InvoiceAgent           ──► SQLite (invoice, invoice_items)
      ├─► MatcherAgent           ──► SQLite (match_status)
      ├─► ExceptionHandlerAgent  ──► SQLite (exceptions)
      ├─► PaymentProcessingAgent ──► SQLite (payments, invoice)
      ├─► StatusAgent            ──► SQLite (invoice, match_status)
      ├─► VendorCommunicationAgent──► SQLite + LLM (vendor message)
      └─► ReportingAgent         ──► SQLite (aggregate queries)
```

Each agent overrides `generate_reply()` with a keyword-based relevance check before doing any work, which keeps the token spend low and the conversation from going in circles.

---

## Database schema

```
vendor                  purchase_order       purchase_order_items
──────                  ──────────────       ────────────────────
vendor_id (PK)          po_number (PK)       id (PK)
name                    vendor_id (FK)       po_number (FK)
email                   order_date           item_code
phone                                        quantity
                                             unit_price

goods_receipt           goods_receipt_items
─────────────           ───────────────────
gr_number (PK)          id (PK)
po_number (FK)          gr_number (FK)
receipt_date            item_code
                        quantity_received

invoice                 invoice_items        match_status
───────                 ─────────────        ────────────
invoice_no (PK)         id (PK)              po_id (PK)
po_number (FK)          invoice_no (FK)      status
vendor_id (FK)          item_code            details
invoice_date            quantity
total_amount            unit_price
status
date_received           payments             exceptions
amount_paid             ────────             ──────────
                        payment_id (PK)      exception_id (PK)
                        invoice_no (FK)      po_number
                        payment_date         issue_type
                        amount_paid          details
                        status               status
                                             timestamp
```

---

## Getting started

**Prerequisites:** Python 3.10+, an Azure OpenAI (or standard OpenAI) API key.

```bash
# 1. Clone and install dependencies
git clone https://github.com/<your-username>/procurement-agent.git
cd procurement-agent
pip install -r requirements.txt

# 2. Add your LLM credentials
cp config_list.example.json config_list.json
# Edit config_list.json with your API key and endpoint

# 3. Create the database and load sample data
python schema.py
python seed_data.py

# 4. Run
python main_groupchat.py
```

---

## Example interactions

```
📥 Instruction: process invoice INV4001 for PO1001, vendor V001,
                date 2024-02-01, total 2000, item ITEM-A qty 100 price 10

📥 Instruction: run 3-way match for PO1001

📥 Instruction: process payment for invoice INV4001

📥 Instruction: what is the status of invoice INV4001

📥 Instruction: generate report total billed per vendor

📥 Instruction: send vendor status update for vendor V001
```

---

## Configuration

`config_list.json` follows the standard AutoGen format:

```json
[
  {
    "model": "gpt-4o-mini",
    "api_type": "azure",
    "api_key": "YOUR_KEY",
    "base_url": "https://YOUR_ENDPOINT.openai.azure.com/",
    "api_version": "2024-03-01-preview"
  }
]
```

The file is in `.gitignore` — never commit API keys.

---

## Project structure

```
procurement-agent/
├── agents/
│   ├── __init__.py
│   ├── invoice_agent.py
│   ├── matching_agent.py
│   ├── exception_agent.py
│   ├── payment_agent.py
│   ├── status_agent.py
│   ├── vendor_agent.py
│   └── reporting_agent.py
├── db/                        # created at runtime, gitignored
├── config.py                  # loads and caches LLM config
├── config_list.example.json   # template — copy to config_list.json
├── main_groupchat.py          # entry point
├── run_sql.py                 # thin SQLite wrapper
├── schema.py                  # CREATE TABLE statements
├── seed_data.py               # sample data for local testing
└── requirements.txt
```

---

## Design notes

- **Parameterised queries everywhere** — `run_sql(query, params)` uses `cursor.execute(query, params)` throughout, so there's no SQL injection surface even when agent-generated values are passed in.
- **No positional column access** — agents query only the columns they need by name rather than indexing into raw result tuples, so schema changes don't silently break things.
- **INSERT OR REPLACE on match_status** — re-running a match always reflects the latest quantities rather than failing on a duplicate primary key.
- **Agents stay in their lane** — each `generate_reply` starts with a keyword check and returns an empty string if the message isn't relevant to that agent. This keeps the LLM calls and the conversation rounds to a minimum.
- **LLM used only where language matters** — invoice SQL generation and the vendor message are LLM tasks; everything else (matching arithmetic, status lookups, payment logic) is plain Python + SQL.

---

## Possible extensions

- Swap SQLite for PostgreSQL with minimal changes to `run_sql.py`.
- Add an approval step before payment (human-in-the-loop via `human_input_mode="ALWAYS"`).
- Expose the group chat as a REST API with FastAPI for integration with a front-end drag-and-drop builder.
- Add structured logging to the `logs` table for a full audit trail.
