# F4 — Milan Explanation (Pointer)

F4 is not covered by a Milan chapter. There is nothing to explain from a Milan retype for this feature.

## Milan's related discipline (informative only)

Milan Janosov's Urban Analytics Advanced course consistently documents the source of every dataset in a markdown cell above the download call. Example from his NYC Parks work:

```markdown
## Data source
NYC Open Data — Parks Properties (updated 2024-11-01)
Endpoint: https://data.cityofnewyork.us/resource/enfh-gkve.geojson
License: NYC Public Data (no restrictions)
```

That's the discipline F4 formalizes. Instead of a paragraph in a notebook that gets lost in git history, we write a machine-readable `.source.yaml` file next to the data itself.

## Why formalize it?

Milan's paragraph works for a course notebook that a single instructor maintains. It breaks down when:

1. Multiple people touch the codebase
2. A pipeline auto-runs 10+ ingestion functions
3. A paid deliverable needs an audit trail

At MVP scale, `.source.yaml` sidecars are overkill. At paid-deliverable scale, they're the difference between a defensible report and a licensing complaint.

## Where to go next

Open [03_oohscout_adaptation.ipynb](03_oohscout_adaptation.ipynb) — the runnable notebook that writes sidecars for F1's and F2's outputs.

For the WHY behind each design choice, read [04_adaptation_explanation.md](04_adaptation_explanation.md) after you've worked through 03.
