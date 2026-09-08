# Building OOHScout: Step 4 - The Database Writer (`authoring.py`)
*Date: August 31, 2026*

In Step 3, we built `project.py` to act as a strict "Bouncer" for our data in Python. But data in Python is ephemeral—it disappears when the server turns off. We need to save it to our PostgreSQL/PostGIS database.

This is where Step 4 (`authoring.py`) comes in. 

## What is `authoring.py`?
In the GeoLibre architecture, `authoring.py` is the only file allowed to perform "side effects" (like saving a file to disk or writing to a database). 

For OOHScout, `authoring.py` will serve as the exclusive gateway to PostgreSQL. It is the bridge that connects the pure data schemas from `project.py` and the security guardrails from `security.py` directly to the database.

## How it works (The Workflow)

1. **The Request:** The AI Agent decides it found a good billboard site and wants to save it. It outputs a JSON object.
2. **The Bouncer:** `authoring.py` catches that JSON and tries to convert it into a `Candidate` object using `project.py`. If the AI hallucinates, it crashes here.
3. **The Guardrails:** If the AI is trying to run custom SQL directly, `authoring.py` passes the query through `check_sql_safety()` from `security.py` to ensure it doesn't contain `DROP TABLE`.
4. **The Execution:** `authoring.py` connects to PostgreSQL (using the modern `psycopg` async driver) and executes the `INSERT` statement using strict parameter binding.
5. **The Sanitization:** If the database crashes, `authoring.py` catches the error, scrubs the passwords out of it using `sanitize_error()`, and returns a safe error message.

By funneling all database interactions through this single file, we ensure that no rogue SQL or unvalidated data can ever touch the source of truth.
