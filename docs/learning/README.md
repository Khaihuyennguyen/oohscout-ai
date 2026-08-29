# Learning Framework — The 4-File Chapter Pattern

Every chapter session in OOHScout produces exactly **4 files**, kept together in one folder under `docs/learning/chapters/<chapter-slug>/`.

This is designed to build deep chapter understanding while producing a portfolio-quality OOHScout artifact per chapter — no wasted work.

---

## The 4 files, per chapter

### File 1 — `01_milan_original.ipynb`
Milan's original notebook, **retyped by you cell by cell** (do not just copy-paste the whole file).

**Why retype?** Muscle memory + attention to every detail. This is the learning half.

**How to use:**
- Open Milan's original from the course folder (external to project)
- Create a fresh notebook at `01_milan_original.ipynb`
- Type each cell (do not paste), running as you go
- Verify each cell's output matches Milan's

**Time budget:** 2-3 hours per chapter.

---

### File 2 — `02_milan_explanation.md`
Line-by-line explanation of Milan's notebook, written by **me (Claude)** as your mentor.

**Format:** Markdown with code blocks, cell-by-cell walkthrough. Explains:
- What each cell does
- Why Milan chose that approach
- What gotchas exist
- The OOHScout translation preview (one line per cell)

**Time budget:** I write this while you're retyping — you can read it as reference.

---

### File 3 — `03_oohscout_adaptation.ipynb`
Your **OOHScout adaptation** of the chapter, applied to McLennan County / IH-35 / Waco data.

**Structure:**
- Same section headers as Milan's chapter
- Same techniques, different data (Waco instead of Manhattan)
- Persona swap where relevant (billboard operator instead of car-free professional)
- Explicit F#-tagged code cells matching the PRD feature IDs

**Time budget:** 3-4 hours per chapter (typically longer than typing Milan's).

---

### File 4 — `04_adaptation_explanation.md`
Line-by-line explanation of **your OOHScout adaptation**, written by me.

**Format:** Same as File 2 but focused on:
- Why we chose specific parameters for Waco (e.g., `EPS_M = 300` instead of `50`)
- Which PRD features this file implements (F#)
- Sanity checks specific to OOHScout data (e.g., "candidate near Buc-ee's must have `min_fuel < 1`")
- Handoff to the next chapter

---

## Folder layout

```
docs/learning/
├── README.md                   (this file)
│
├── template/                   Copy this folder when starting a new chapter
│   ├── 01_milan_original.ipynb      (empty template with instructions cell)
│   ├── 02_milan_explanation.md      (empty template)
│   ├── 03_oohscout_adaptation.ipynb (empty template)
│   └── 04_adaptation_explanation.md (empty template)
│
└── chapters/
    ├── geoai_ch04_data_prep/        ✅ Done (Ch 4)
    │   ├── (no 01/03 — you did these before adopting the pattern)
    │   ├── 02_milan_explanation.md  ← ch04_explanation.md
    │   └── 04_adaptation_explanation.md ← oohscout_real_txdot_data_explanation.md
    │
    ├── geoai_ch05_segmentation/     ✅ Done (Ch 5)
    │   └── 02_milan_explanation.md  ← ch05_explanation.md
    │
    ├── ua_advanced_ch01_setup/      🚧 Started — F1 in progress
    │   ├── 01_milan_original.ipynb          (you type this)
    │   ├── 02_milan_explanation.md          (I write this in parallel)
    │   ├── 03_oohscout_adaptation.ipynb     (you build with my guidance)
    │   └── 04_adaptation_explanation.md     (I write when you finish)
    │
    ├── ua_advanced_ch02_poi_clustering/    (queued for after Ch 1)
    ├── ua_advanced_ch03_accessibility/     (queued)
    ├── ua_advanced_ch04_landuse/           (queued)
    ├── ua_advanced_ch05_livability/        (queued)
    ├── ua_advanced_ch06_pricing/           (queued)
    └── geoai_ch14_agent/                   (preview allowed after F7; full adaptation Phase 4)
```

---

## Chapter session workflow

**Before you start a chapter:**
1. Copy `template/` to `chapters/<slug>/`
2. Open the four template files and read what each expects
3. Set aside 6-8 hours (can split across days)

**During the chapter session:**
1. Retype Milan's notebook into File 1 (2-3 hrs) — I write File 2 in parallel
2. Update the PRD (`docs/PRD.md`) marking the features you're about to build as "in_progress"
3. Build the OOHScout adaptation in File 3 with my guidance (3-4 hrs)
4. I write File 4 line-by-line
5. Update the PRD marking completed features
6. Update `docs/FEATURES.md` and `docs/MASTER_PLAN.md` feature status
7. Commit the whole chapter folder as one git commit

**After the chapter:**
1. Update `notebooks/ch_progress.md` (chapter-level status log)
2. Consider blog post material for the chapter's insights
3. If a feature broke or ran different than expected, add to PRD Section 12 (Open Questions)

---

## Non-negotiable disciplines per chapter

1. **Retype, don't copy.** File 1 is a learning exercise. Copy-paste means shallow understanding.
2. **Every File 3 code cell tagged with its PRD feature ID** — comment `# F17 — Per-candidate drive-time to advertiser categories`
3. **Every explanation file must include the OOHScout translation table** — mapping Milan's Manhattan concepts to McLennan billboard operator concepts.
4. **No skipping section headers.** Even if a section is short, keep the Milan → OOHScout structural parallel.
5. **Sanity checks are code, not comments.** Every join has an `assert`.
6. **Bad output = stop and diagnose.** Do not proceed to next cell if the previous cell's output looks wrong.

---

## Why this pattern?

- **Learning depth:** retyping + explaining forces deep understanding
- **Portfolio artifact:** the adaptation notebook is directly showable to recruiters
- **Reproducibility:** anyone can clone the repo and re-run each chapter
- **Auditability:** every OOHScout technique traces to a course chapter
- **Skill transfer:** after N chapters, your ability to read + adapt any GeoAI paper is transformed

---

## What NOT to do

- Do not skip File 1 (Milan's retype) — even if you "know it already"
- Do not skip File 4 (adaptation explanation) — future you will need it
- Do not build features not in the PRD — if a chapter suggests a feature, add it to PRD first
- Do not commit until all 4 files exist and pass a quick review

## Early agent learning boundary

After F7, a small Chapter 14 learning exercise may wrap **read-only Track A tools** in an experimental Scout shell. This is an interface checkpoint, not a new PRD feature and not completion of F37. It cannot combine Track A with Track B, perform geometry in the LLM, or recommend where to build. The full `03_oohscout_adaptation.ipynb` for Chapter 14 remains a Phase 4 activity.
