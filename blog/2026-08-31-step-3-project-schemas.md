# Building OOHScout: Step 3 - The Data Schemas (`project.py`)
*Date: August 31, 2026*

As we move to Step 3 of building OOHScout AI, we need to establish exactly how we define our data. In GeoLibre, they use a file called `project.py` that strictly defines what a map, a layer, and a legend look like. 

For OOHScout, we are adopting this same pattern to define our domain-specific concepts: **Corridors** and **Candidates**.

## What is `project.py`?
In software engineering, it is crucial to separate the *structure* of your data (the "nouns") from the *actions* you take on that data (the "verbs").

* `project.py` will contain our "nouns". It defines the strict rules for what makes a valid Corridor or Candidate. It doesn't know how to save to a database or talk to the internet. It only knows how to structure data perfectly.
* (Later, in Step 4, `authoring.py` will contain our "verbs"—the logic that actually saves these structures into the PostgreSQL database).

## What are we defining?

### 1. The `Corridor` Schema
A corridor is a specific stretch of highway you are scouting (e.g., "IH-35 through McLennan County"). In `project.py`, we will define a `Corridor` to require:
* A unique ID and a Name.
* A spatial geometry (the actual physical bounds of the highway stretch).
* Rules and metadata (e.g., specific zoning restrictions applied to this corridor).

### 2. The `Candidate` Schema
A candidate is a specific parcel of land that might be suitable for a billboard. We will define a `Candidate` to require:
* A reference to its parent Corridor.
* Its own spatial geometry (the parcel bounds).
* A strict Regulatory Status field (`PASS`, `FAIL`, or `REVIEW`). As defined in our project rules, this must be a hard gate, not a soft weighted score.
* A "Legal" rule check: We must explicitly forbid labeling any candidate as "LEGAL" in the code, enforcing our compliance rule that only humans determine final legality.

## Why this GeoLibre pattern matters
By creating these strict, pure data definitions in `project.py`, we guarantee that by the time the AI tries to save a Candidate to the database, the data is already perfectly formatted and validated. If the AI hallucinates a regulatory status like "MAYBE", `project.py` will instantly reject it before it ever reaches the database.
