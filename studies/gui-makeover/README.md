# Workspace GUI makeover — research

A prettification + IA-reorganization + newcomer-learnability makeover of the PySide6 **Workspace**
(`ff9mapkit/ff9mapkit/workspace/`). Research pass, 2026-07-14 — a plan to attack in phases, not yet implementation.

- **[PLAN.md](PLAN.md)** — the deliverable: north-star, principles, the three evidenced problems, cross-cutting
  foundations (token system / IA / learnability / cohesion spine / a11y), an 11-phase plan (P0–P10) with
  goal/scope/deps/effort/risks/success-criteria each, sequencing, guardrails, and **6 open questions for the user**.
- **[research/](research/)** — the source material the plan synthesizes:
  - `report_screenshots.md` · `report_designSystem.md` · `report_iaNav.md` · `report_learnability.md` ·
    `report_featureDensity.md` — the five audits of the actual GUI.
  - `report_resTokens.md` · `report_resProgressive.md` · `report_resOnboarding.md` · `report_resA11y.md` —
    the four external best-practice research streams (design tokens, progressive disclosure, onboarding, accessibility).
  - `DRAFT.md` + `CRITIQUE.md` — the pre-revision draft and the adversarial critique that hardened the final plan.
- **[evidence/](evidence/)** — offscreen screenshots of populated Workspace states (GUI chrome only, no game art).

Reproduce a screenshot: render the real shell offscreen on the **native** Windows platform (not
`QT_QPA_PLATFORM=offscreen` — that gives tofu boxes): `Workspace(pal)` with
`pal = editor.theme.pick_palette(mode)`, `_apply_app_theme(app, pal)`, `WA_DontShowOnScreen`, `show()`,
`processEvents()`, `grab().save(...)`, env `FF9MAPKIT_NO_THUMBS=1`.
