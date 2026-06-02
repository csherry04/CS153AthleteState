# Agent Implementation Summary

## What Is Built

The project has a tool-grounded coaching layer over the athlete state model:

- `src/agent_tools.py` exposes local monitoring tools backed by generated CSV/JSON outputs.
- `src/coach_api.py` provides the live FastAPI coach endpoint.
- `scripts/run_coach_api.py` starts the backend and loads `.env` if present.
- `scripts/run_coaching_agent.py` provides a CLI/demo path.
- `scripts/generate_coaching_qa.py` writes static example coach questions and answers.

## Live Coach Flow

```text
User question
  -> web Coach page
  -> POST /api/coach
  -> local fast answer or tool prefetch
  -> chat completion with tool definitions when needed
  -> cleaned, grounded response
```

The live backend uses `OPENAI_API_KEY` from the environment or local `.env`.

## Static Coach Flow

```text
scripts/generate_coaching_qa.py
  -> curated example payload
  -> outputs/analysis/coaching_qa.json
  -> canvases/coaching-qa.canvas.tsx
```

This page is meant to show what coach answers should look like without depending on API availability.

## Tool Layer

The tool layer can answer questions about:

- daily scores, alert tiers, recommendations, and attribution
- day/period comparisons
- recent trends and highlighted days
- progression and recovery context
- model disagreement
- simple volume/down-week simulations
- frontier outcome evaluation and athlete profile summaries

## Validation

Recommended checks:

```bash
python -m py_compile src/coach_api.py src/agent_tools.py scripts/run_coach_api.py scripts/run_coaching_agent.py
python scripts/run_coaching_agent.py --demo
cd web && npm run build
```

## Notes

- The live coach is only as current as the generated analysis outputs.
- Counterfactuals are heuristic unless the relevant scoring path is explicitly rerun.
- The agent is for monitoring and explanation, not diagnosis.
