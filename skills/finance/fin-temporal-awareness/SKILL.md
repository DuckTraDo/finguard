---
name: fin-temporal-awareness
description: Time-aware workflow for finance questions that use words like latest, current, today, tomorrow, or as of. Load this when a finance answer needs explicit dates or date ranges instead of ambiguous relative time.
version: 0.1.0
author: FinGuard
license: MIT
metadata:
  hermes:
    tags: [finance, temporal, dates, time-sensitive]
    related_skills: [fin-source-citation]
---

# Fin Temporal Awareness

Use this skill when a finance question depends on timing. Financial answers can
become misleading if they rely on words like "latest", "current", "today", or
"as of" without stating the actual date or date range.

## When to Use

- The user asks for the latest, current, most recent, or as-of finance information
- The question references today, tomorrow, yesterday, or another relative time word
- The answer depends on a quarter, filing period, market close, publication date, or event date
- You need to compare values across different dates or date ranges

## Core Workflow

1. Translate relative time terms into explicit dates or date ranges whenever possible.
2. Distinguish the relevant clock:
   event date, filing date, publication date, market date, or reporting period.
3. If freshness is uncertain, say so clearly instead of implying the answer is current.
4. Prefer phrases like `As of YYYY-MM-DD` or `For Q4 2023` over vague temporal wording.
5. If sources disagree on timing, surface that mismatch instead of collapsing them into one claim.

## Rules

1. Never answer a time-sensitive finance question with relative-time language alone.
2. If the captured sources do not establish a date, say that the date could not be confirmed.
3. Keep date logic simple and visible to the user.
4. When comparing periods, state both periods explicitly.
5. Do not silently mix stale and current figures in one sentence.

## Output Pattern

- Main answer with explicit date or period anchors
- Cite the source date when it matters to the interpretation
- Use `Verification note:` if freshness or timing could not be confirmed

## Anti-Patterns

- Saying "latest inflation reading" without naming the reading date
- Quoting a stock price without the market date or timestamp
- Treating a filing publication date as the same thing as the fiscal period it covers
- Mixing "today" and "2023" in the same answer without clarifying the comparison window
