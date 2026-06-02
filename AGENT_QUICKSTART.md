# Quick Start: Coaching Agent

## Offline Demo

```bash
cd /Users/callumsherry/athlete-state-model
python scripts/run_coaching_agent.py --demo
```

This exercises the local tools without any API call.

## Live Coach

```bash
export OPENAI_API_KEY=your_key_here
python scripts/run_coach_api.py
```

In another terminal:

```bash
cd web
npm run dev
```

Open the web app and use `Coach (live)`.

## Static Examples

```bash
python scripts/generate_coaching_qa.py
```

This refreshes the static `Coaching QA` examples page. It is intentionally an example page, not a generated answer log.

## What You Get

- Tool-grounded answers from local monitoring outputs.
- Fast local answers for common date/risk questions.
- Live synthesis when the backend needs to combine tool results.
- Static example answers for demos that should not depend on an API call.

## Key Files

| File | Purpose |
|---|---|
| `src/agent_tools.py` | Tool definitions and local data access |
| `src/coach_api.py` | FastAPI backend for the live coach |
| `scripts/run_coach_api.py` | Starts the live coach backend |
| `scripts/run_coaching_agent.py` | CLI agent and offline demo mode |
| `scripts/generate_coaching_qa.py` | Static coaching examples generator |
| `canvases/coaching-qa.canvas.tsx` | Static examples page |

## Checks

```bash
python -m py_compile src/coach_api.py src/agent_tools.py scripts/run_coach_api.py scripts/run_coaching_agent.py
cd web && npm run build
```
