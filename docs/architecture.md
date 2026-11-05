# Architecture

## Current execution flow

1. `main.py` receives a natural-language instruction.
2. `AgentBrain` sends the instruction to the local Ollama API.
3. Ollama returns a structured JSON action plan.
4. `parse_plan` validates the action against a strict allowlist.
5. `ToolDispatcher` maps the validated action to an implemented tool.
6. `BrowserController` opens a visible Chromium browser and performs the YouTube search.

## Design principles

- **Local-first:** inference is sent to the configured local Ollama endpoint.
- **Explicit capabilities:** the model can request only known actions.
- **Validation before execution:** model output is treated as untrusted input.
- **Separation of concerns:** planning, dispatching, browser control, and configuration are separate modules.

## Planned evolution

LangGraph can be introduced when the workflow needs stateful nodes, retries, approval checkpoints, or multiple specialized agents. FastAPI and voice interfaces should be added after the CLI workflow is reliable.
