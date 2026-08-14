# manufacturing-troubleshooting-agent

> This repository is a public reimplementation using synthetic data.
> It contains no proprietary code, internal data, confidential materials, or company-specific assets.

`manufacturing-troubleshooting-agent` is a FastAPI + SQLite portfolio demo for a manufacturing-floor troubleshooting assistant. It is intentionally simple, transparent, and designed to show a safe Agent workflow that recruiters and interviewers can understand quickly.

## V1 scope

- Problem input UI
- Multi-round follow-up questions
- Synthetic knowledge base
- Simple keyword-based knowledge retrieval
- Risk rules
- Structured Agent Result
- Knowledge source display
- Risk Level
- Human Escalation
- Simple case records
- Several test cases and bad cases

## Core workflow

Problem input  
→ follow-up when information is insufficient  
→ knowledge retrieval  
→ risk / rule judgment  
→ structured troubleshooting result  
→ human escalation when required  
→ retained case record

## Safety boundary

This demo does **not** provide direct unreviewed high-risk actions or quantitative machine-setting instructions.

When:

- information is insufficient
- knowledge coverage is insufficient
- risk is elevated

the Agent explicitly routes to human review / escalation.

## Tech stack

- Python 3.11
- FastAPI
- SQLite
- Jinja2 templates
- Tailwind via CDN

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Synthetic data used

The demo includes only fictional examples such as:

- synthetic troubleshooting knowledge entries
- synthetic source IDs like `KB-OPS-001`
- synthetic cases like conveyor stop, paint surface defect, chiller fluctuation, injection short shot, and motor overload
- synthetic test cases and bad cases

No real company names, internal documents, production records, private repositories, or proprietary knowledge are included.

## Repository safety statement

This repository is a public reimplementation using synthetic data.
It contains no proprietary code, internal data, confidential materials, or company-specific assets.
