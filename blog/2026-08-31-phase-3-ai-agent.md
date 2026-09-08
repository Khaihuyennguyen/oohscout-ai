# Building OOHScout: Phase 3 - The AI Agent (MCP)
*Date: August 31, 2026*

In Phase 1, we built a highly secure data vault. In Phase 2, we built the API (the secure door to the vault). Now, in Phase 3, we are finally ready to introduce the AI to the system. 

We do this using the **Model Context Protocol (MCP)**, which allows us to safely connect an AI Agent (like Claude) to our local data. Phase 3 consists of three critical steps:

## Step 8: The Sandbox (`mcp/workspace.py`)
AI Agents sometimes need to read or write physical files on your hard drive. For example, the agent might need to read a massive GeoJSON file of Texas highway corridors, or save a `.csv` of potential candidates. 

If you give an AI unrestricted access to your hard drive, a prompt injection attack could trick the AI into reading your personal passwords or deleting system files. 
`workspace.py` creates a "Sandbox" (or a prison). It intercepts every file read/write request from the AI, checks the file path, and completely blocks the action if the file is outside of the designated `backend/src/oohscout/data/` folder.

## Step 9: The Toolbelt (`mcp/server.py`)
An AI cannot inherently talk to a PostgreSQL database. We have to teach it how by giving it "Tools."
`server.py` takes the secure Python functions we built in Phase 1 (like `save_candidate` in `authoring.py`) and wraps them in an MCP `@tool` decorator. 

This magically exposes the function to the AI's interface. Claude will suddenly see a button it can press called `add_billboard_candidate`. When Claude presses it, the request flows securely through our Phase 2 API and into our Phase 1 Vault.

## Step 10: The Brain (`skills/SKILL.md`)
Even if the AI has the tools and is in a sandbox, it doesn't know *what* it is supposed to do. 
The final step is writing the master instruction manual. This is the System Prompt that tells the AI: *"You are an expert Geospatial Engineer. Your goal is to use the `add_billboard_candidate` tool. You must never estimate distances yourself. Always wait for the database to calculate them."*

Once these three steps are complete, OOHScout becomes a fully autonomous, highly secure billboard intelligence engine.
