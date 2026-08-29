# Chapter [N] — OOHScout Adaptation: Line-by-Line Explanation

**Chapter:** [Course name] Chapter [N]
**Adaptation file:** `03_oohscout_adaptation.ipynb`
**PRD features implemented:** F[X], F[Y], F[Z]

---

## Adaptation goal (in one sentence)
[What does this adaptation produce for OOHScout at the end?]

## Waco-specific parameter choices vs Milan's defaults

| Parameter | Milan's default (Manhattan) | Your choice (Waco) | Why |
|---|---|---|---|
| `PLACE` | `"Manhattan, New York"` | `"McLennan County, Texas"` | Study area |
| `CRS_METRIC` | `32618` (UTM 18N) | `32614` (UTM 14N) | Texas is in UTM zone 14 |
| ... | ... | ... | ... |

---

## Section-by-section walkthrough

### Section 1 — [Title]

**PRD features this section implements:** F[X], F[Y]

**Cell 1:**
```python
# F1 — Retargetable study area
# code here
```
Explanation:
- Line 1: [what]
- Line 2: [what]
- OOHScout-specific choice: [what's different from Milan]

...

---

## Sanity checks (asserts you must verify)
- [ ] `assert candidates['candidate_id'].is_unique`
- [ ] `assert candidates_in_park['park_dist_m'].max() < 1.0` — inside means ~0m
- [ ] [Chapter-specific sanity check]

## Files produced
| Filename | Contents | Loaded by |
|---|---|---|
| `data/mclennan_[X].gpkg` | [what] | Chapter [N+1] |
| `data/[X].csv` | [what] | [where] |

## What the operator sees
[If this chapter produces a customer-facing artifact, describe it.]

## Handoff to next chapter
Chapter [N+1] will load `[filename]` and add [features].

## Update the PRD
After this chapter, mark the following features complete in `docs/PRD.md`:
- [ ] F[X] — [name]
- [ ] F[Y] — [name]

## Portfolio-worthy insights from this chapter
[What did you learn that would make a good LinkedIn post or blog paragraph?]
