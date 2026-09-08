# Building OOHScout: Architectural Decisions & Tooling
*Date: August 31, 2026*

## 1. Why Gemini 3.1 Pro is Better for Coding than Flash

When building a complex application like OOHScout AI, choosing the right model is critical. The main difference between the **Pro** (Gemini 3.1 Pro) and **Flash** models comes down to the balance of reasoning capability versus speed and efficiency.

* **Gemini 3.1 Pro:** Built for complex reasoning, heavy logical deduction, and intricate coding tasks. It is best used for multi-step planning, large-scale architectural refactors, difficult debugging, and understanding deeply intertwined codebases. It takes slightly longer to process but delivers the highest quality for hard problems.
* **Gemini Flash:** Built for sheer speed, low latency, and high-efficiency processing. It is best for high-volume or simpler tasks like quickly summarizing logs, extracting data from files, or powering lightweight subagents that need to report back instantly.

For OOHScout, which requires strict architectural rules (like separating spatial math from database writes), Gemini 3.1 Pro is the necessary choice for architecting and writing the code.

## 2. Refactoring `pyproject.toml` (GeoLibre's Pattern)

Our very first step in building OOHScout was refactoring `pyproject.toml`. 

**The Problem:** The original file listed every single library in one giant group. That meant if a developer just wanted to run a tiny script, their computer still had to download 5 Gigabytes of heavy machine-learning and map-rendering tools, making the app slow to start and annoying to install.

**The Solution:** We adopted GeoLibre's pattern of **"Optional Dependencies."** We chopped the recipe up into highly specialized, bite-sized categories:
* **The Core:** Only the bare minimum to start the app (like `fastapi`).
* **`[vector]`:** Only map and shape-drawing tools (like `geopandas` and `shapely`).
* **`[postgis]`:** Only the tools needed to talk to the database (`psycopg`).
* **`[rag]`:** Only the heavy AI text-processing tools.
* **`[agent]`:** Only the AI orchestration tools (`langgraph`).
* **`[all]`:** A master switch that installs everything at once.

This keeps the foundation incredibly clean and modular, allowing fast, isolated installations.

## 3. Core Architectural Decisions (The "Grill-Me" Session)

Before writing the backend logic, we made several strict decisions to ensure OOHScout remains secure and focused on its specialized domain (billboard site intelligence):

1. **Source of Truth:** Unlike GeoLibre's local JSON files, the **PostgreSQL Database** is the absolute source of truth. PostGIS owns all spatial measurements.
2. **Write Access:** The AI will write **raw SQL** directly to the database.
3. **Security Boundary:** We secure this by switching to a dynamic **`writer` role** at the database level when necessary, applying least-privilege access.
4. **Context Grounding:** The exact `CREATE TABLE` schemas will be hardcoded directly into the AI's system prompt, so it never has to guess table structures.

By combining GeoLibre's defensive mindset with these OOHScout-specific rules, we ensure the AI builds exactly what is needed without hallucinating generic solutions.
