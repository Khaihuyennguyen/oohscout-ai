# Building OOHScout: Step 9 - The Toolbelt (`mcp/server.py`)
*Date: August 31, 2026*

With our secure database (Phase 1) and secure API (Phase 2) complete, we have a problem: Large Language Models (like Claude) cannot natively write to a PostgreSQL database. They only know how to generate text.

To bridge this gap, we use the Model Context Protocol (MCP) to build a **Toolbelt** (or a "Menu"). 

## What is `server.py`?
Inside `mcp/server.py`, we take the secure Python functions we wrote earlier and wrap them in a special `@tool` decorator. 

For example, we take our heavily-guarded `save_candidate()` function from `authoring.py`, and we wrap it in a tool called `add_billboard_candidate`. 

## How it prevents Hallucinations
When we give the AI a tool, we also provide a strict "Schema" (a rulebook) for how to use that tool. 
We tell the AI: *"You have a tool called `add_billboard_candidate`. If you want to use it, you MUST provide a `corridor_id` and a `regulatory_status`. The status CANNOT be 'LEGAL'. It must be 'PASS', 'FAIL', or 'REVIEW'."*

If the AI gets confused and tries to press the button with bad data, the tool physically rejects the button press before the code even runs.

## Coordinating the Workflow
Eventually, this file will hold all the tools for OOHScout. It will have tools for the Database, tools for the GIS spatial math, and tools for the RAG PDF reader. The AI simply looks at this menu of tools and decides which order to press the buttons in to find an eligible billboard site!
