# FinGuard arXiv / Overleaf Submission Checklist

Status: submission closeout notes. This file does not change experiments, benchmark logic, model behavior, or reported results.

## Minimal Overleaf Upload Package

Upload only these files from `benchmarks/finguard/overleaf/`:

- `main.tex`
- `references.bib`

Do not upload benchmark datasets, smoke outputs, Python code, local model logs, or intermediate markdown notes unless the submission explicitly needs supplementary material.

## Compile Checklist

- Set `main.tex` as the Overleaf root file.
- Compile with `pdfLaTeX` first; the current skeleton uses `article`, `natbib`, `booktabs`, `hyperref`, and `url`.
- Confirm `references.bib` is detected and all `\citep{...}` entries resolve.
- Recompile until references, citations, and table labels stabilize.
- Check for missing citations shown as `?` or `[?]`.
- Check for overfull `\hbox` warnings, especially in the two result tables with long column names.
- If a table overflows, first reduce column labels or switch to `table*`; do not change metric values.
- Confirm appendix starts after `\appendix` and that the failure typing table is not counted as a main result.
- Confirm all numeric metrics remain at three decimals.
- Confirm no author placeholder remains before final upload.

Local note: this machine did not have `pdflatex` available during preparation, so the current validation is static rather than a PDF compile.

## Author / Affiliation Placeholders To Replace

In `main.tex`, replace:

- `Author Name(s)`
- `Institution / Lab / Independent Research`
- `email@example.com`

Optional before submission:

- Add equal-contribution or corresponding-author markers if needed.
- Add ORCID or project page only if the venue/arXiv metadata benefits from it.
- Decide whether to list the work as independent research or under an institutional affiliation.

## Pipeline Figure Plan

Recommended placement: after the Introduction or at the start of Method.

Recommended figure type: one horizontal pipeline diagram, single column if compact or two-column width if using a workshop template.

Core elements:

- User financial query.
- FinGuard Guard layer: query type, expected behavior, temporal intent, compliance/refusal route.
- Benchmark local smoke profile: short system prompt, tools disabled, continuation disabled, `think=false`, local endpoint.
- Base model path: Gemma 31B / Qwen3.5-27B local generation.
- Source / trace compatibility layer: source normalization and missing-source fail-soft handling.
- FinVerify layer: numeric claim checks, source/citation alignment, conservative downgrade.
- Final assistant response.
- Benchmark observer: metadata refusal, raw visible refusal, aligned visible refusal, behavior-safe rate, over-refusal.

Suggested caption:

> FinGuard wraps a Hermes-style financial assistant with a pre-generation guard and post-generation verification layer. The local smoke profile disables tools and continuation to isolate refusal routing, visible safety, numeric traceability, and observation alignment from full-agent behavior.

Design notes:

- Use dashed boxes for benchmark-only components, such as local smoke profile and observer alignment.
- Use solid boxes for runtime wrapper components, such as Guard and Verify.
- Do not imply that naive RAG or Qwen was part of the full Hermes agent path.
- Make clear that Gemma and Qwen were served sequentially through the same endpoint, not concurrently.

## Paper-Style Final Polish Suggestions

- Abstract is strong but dense; if page pressure appears, remove one clause from the first sentence rather than deleting the Gemma/Qwen distinction.
- The main Gemma table is essential. Keep it in the main text.
- The cross-model table is essential because it supports the wrapper-architecture claim. Keep it in the main text.
- The category breakdown is already compressed enough; keep it as prose unless a reviewer needs per-category detail.
- Keep failure typing in the appendix. It is valuable but too diagnostic for the main narrative.
- Consider shortening `metadata refusal accuracy` to `metadata refusal` in table headers if Overleaf reports overfull boxes.
- The Qwen citation is currently a model-card-style BibTeX entry; verify the final official citation before arXiv upload.
- The phrase `Hermes-style assistant` should either cite the actual Hermes project, if public, or be softened to `agentic financial assistant` if Hermes is private.
- The claim boundary is appropriately conservative. Avoid adding stronger claims about full-agent performance, EDGAR grounding, or production traffic unless new experiments are added later.
