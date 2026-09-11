"""OOHScout MCP server — deferred to Phase 3.

The prototype tools that lived here were removed on 2026-09-10. They reported
"success" against a mock database connection and let the model supply a
candidate's regulatory status and setback distance, which the spatial engine
must compute instead.

MCP returns in Phase 3 as a front door to read-only Track A tools (candidates,
spacing screening, scores), next to the web UI. Until then this module
registers nothing.
"""
