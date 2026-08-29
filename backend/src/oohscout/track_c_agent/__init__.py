"""Track C — ReAct Agent Orchestration.

Wraps Track A and Track B as tools. Never calculates directly.
Modules (to be built):
- tools: tool registry with Pydantic schemas
- react_loop: Thought/Action/Observation loop
- llm_client: LLM wrapper (Claude by default)
- evaluations: golden test cases
"""
