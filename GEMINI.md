# OOHScout AI — Agent Rules

## RULE 1: Read Before You Speak
Before answering ANY question about what is built, what is done, or what to do next:
1. Read the relevant source files using file tools.
2. Run `git status --short` to see what is committed vs untracked.
3. Read `docs/FEATURES.md` for the authoritative feature list and statuses.
4. Read `CLAUDE.md` for the project rules, architecture decisions, and session progress.

**NEVER answer from memory. NEVER assume a file exists or a feature is complete without reading it.**

If you are asked "what is done?", the only valid answer comes from `git status` + `docs/FEATURES.md`. Not from what you wrote in a previous session.

---

## RULE 2: Git Status = Ground Truth
The only things that are "done" are things that:
- Have a ✅ in `docs/FEATURES.md`, AND
- Are committed to `main` (not just on a feature branch, not untracked)

Untracked files (`??` in git status) are **scaffolded, not done**.

---

## RULE 3: Never Overstate Status
Words like "complete", "finished", "done", "built" must only be used if the feature passes the gate in Rule 2.

Use precise language instead:
- "Scaffolded but not committed" — files exist, no tests, not in main
- "In-flight" — on a feature branch, not yet merged
- "Shipped" — committed and merged to main with passing tests

---

## RULE 4: Feature Numbering Comes From docs/FEATURES.md
When referencing features (F1, F5, F6, F7 etc.), always look them up in `docs/FEATURES.md`. Do not describe a feature from memory.

For example:
- F5 = DEV_MODE bounding box around Waco urban core (NOT "parcel loader")
- F6 = Corridor buffer (500m search zone around IH-35) (NOT "setback math")
- F7 = Candidate site sampling every 1km along centerline (NOT "setback math")
- Setback math = F9, depends on Track B research

---

## RULE 5: Security Rules Come From CLAUDE.md
Before writing or reviewing any security code, read CLAUDE.md rules 9-19 (§S1-S17). In particular:
- Rule 11: `check_sql_safety()` must allow SELECT/WITH ONLY. Not INSERT/UPDATE/DELETE.
- Rule 15: Every path must resolve inside the Workspace root using `Path.resolve()` BEFORE the containment check.
- Rule 14: Every MCP tool must be wrapped by `_reports_its_errors`.

---

## RULE 6: Architecture Comes From V2, Not Memory
The authoritative architecture reference is `docs/PRODUCTION_ARCHITECTURE_V2.md`.
Do not re-derive architecture decisions. If V2 has a pattern, use it.

---

## RULE 7: Never Promote the Frontend
The web dashboard (React + MapLibre) is **deferred until payment signal**.
Do NOT include it as a numbered phase in any roadmap. It is optional and Phase 6+ only.
