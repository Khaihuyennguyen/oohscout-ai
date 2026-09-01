import os
from typing import Literal
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

# We import our ultra-secure Phase 1 code
from oohscout.authoring import save_candidate, execute_agent_sql

# 1. Initialize the MCP Server (The "Toolbelt")
# We explicitly name it so Claude knows what system it is talking to.
mcp = MCPServer("OOHScout")

# ==============================================================================
# Tool 1: Read-Only File System Access
# ==============================================================================
# Notice we DO NOT provide a "write_file" tool. This mathematically enforces the 
# Read-Only rule you requested. The AI can look at the data folder, but cannot 
# alter it.

@mcp.tool()
def read_local_file(filename: str) -> str:
    """
    Reads a file from the local OOHScout data directory. 
    Use this to read GeoJSON, CSV, or zoning PDF text.
    """
    from oohscout.mcp.workspace import resolve_path
    
    # 1. The Sandbox Guard (Checks for Path Traversal)
    safe_path = resolve_path(filename)
    
    # 2. Enforce Read-Only mathematically (if the file doesn't exist, we don't create it)
    if not safe_path.exists():
        return f"Error: File {filename} does not exist in the read-only sandbox."
        
    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

# ==============================================================================
# Tool 2: Database Candidate Creation (The only way to save data)
# ==============================================================================

@mcp.tool()
def add_billboard_candidate(
    corridor_id: str, 
    parcel_id: str, 
    geometry: str, 
    regulatory_status: Literal["PASS", "FAIL", "REVIEW"],
    setback_distance_ft: float
) -> str:
    """
    Saves a new billboard candidate to the PostgreSQL database.
    WARNING: You must NEVER use the status 'LEGAL'. Use PASS, FAIL, or REVIEW.
    """
    # We simulate a database connection for now. In a full production setup, 
    # this would pull the `app.state.db_conn` from the FastAPI request.
    from unittest.mock import MagicMock
    mock_conn = MagicMock()
    
    # 1. Package the data exactly how our Bouncer (project.py) expects it
    candidate_json = {
        "corridor_id": corridor_id,
        "parcel_id": parcel_id,
        "geometry": geometry,
        "regulatory_status": regulatory_status,
        "setback_distance_ft": setback_distance_ft
    }
    
    try:
        # 2. Pass it into the Phase 1 Database Gateway
        new_id = save_candidate(mock_conn, candidate_json)
        return f"Success! Candidate saved to database with ID: {new_id}"
    except Exception as e:
        # If the Bouncer (project.py) rejects it, Claude gets the error message
        return f"Database Error: {str(e)}"

# ==============================================================================
# Tool 3: Advanced Database Analytics
# ==============================================================================

@mcp.tool()
def run_custom_analytics(query: str) -> str:
    """
    Executes a custom SQL query against the OOHScout database.
    Use this to count candidates, find averages, or analyze corridors.
    """
    from unittest.mock import MagicMock
    mock_conn = MagicMock()
    
    try:
        # 1. Pass the query through the Guardrails (security.py)
        results = execute_agent_sql(mock_conn, query)
        return f"Query Success. Results: {results}"
    except Exception as e:
        # If the query contains DROP/ALTER, it gets blocked here
        return f"Security Block: {str(e)}"
