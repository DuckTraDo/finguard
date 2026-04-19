---
name: fin-source-citation
description: Conservative citation workflow for financial answers with numeric claims, filings, or other time-sensitive facts. Load this when a finance response should be grounded in captured sources instead of unsupported recall.
version: 0.1.0
author: FinGuard
license: MIT
metadata:
  hermes:
    tags: [finance, citations, verification, sources]
    related_skills: [hermes-agent]
---

# Fin Source Citation

Use this skill to keep finance answers grounded when the response includes numbers,
dates, filing references, or other factual claims that should be tied to captured
sources.

## When to Use

- The user asks a finance question with numeric claims or financial ratios
- Tool output contains filings, search results, or source excerpts worth citing
- The answer depends on time-sensitive statements such as "latest", "current", or "today"
- You need to explain that some claims could not be verified from the captured record

## Core Workflow

1. Check the captured sources before finalizing the answer.
2. If the answer contains numbers, make sure each number appears in the captured source text or clearly mark it as unverified.
3. Prefer explicit dates when discussing time-sensitive finance information.
4. Add a short `Sources:` section using the source title when available, otherwise fall back to the tool name.
5. If no captured sources are available, say so plainly instead of inventing a citation.

## Rules

1. Never invent a filing, citation, URL, quote, or timestamp.
2. Never imply that a number was verified if the captured sources do not contain it.
3. If evidence is partial, downgrade certainty with language like "based on the captured sources" or "I could not verify".
4. Keep citations compact. Do not dump raw tool output into the final answer.
5. Stay educational and non-personalized. This skill is about grounding, not giving investment advice.

## Output Pattern

- Main answer first, concise and factual
- Disclaimer only when the surrounding policy/classifier requires it
- `Sources:` block at the end when captured sources exist
- `Verification note:` only when some numeric claims remain unsupported

## Anti-Patterns

- Turning a single search result into a sweeping market conclusion
- Repeating a number from memory when the captured sources do not contain it
- Using relative time words without explicit dates on unstable financial facts
- Padding the answer with extra citations that were never actually captured
