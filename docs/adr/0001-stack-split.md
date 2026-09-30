# Python backend, Bun frontend toolchain, SQLite store

Backend and deterministic investigation tools stay in Python with FastAPI (matches fal stack note and handoff Day 2-3 requirements). React/TypeScript frontend uses Bun for install/dev/build/test instead of npm. SQLite holds cases, evidence, findings, actions, and audit events locally. LLM access goes through a server-side OpenRouter adapter (free-plan, temp 0, strict JSON-Schema validation); the key never reaches the frontend and only redacted synthetic content is sent.
