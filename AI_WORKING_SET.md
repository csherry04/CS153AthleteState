# AI Working Set

For low-token edits, start with these files only unless the task explicitly needs generated data or raw outputs.

## Active localhost app
- `web/src/App.tsx`
- `web/src/styles.css`
- `web/src/canvas/index.tsx`
- `web/src/pages/Coach.tsx`
- `web/vite.config.ts`

## Coach backend
- `src/coach_api.py`
- `src/agent_tools.py`
- `scripts/run_coach_api.py`
- `run_coach_api.py`

## Source-of-truth configs
- `requirements.txt`
- `web/package.json`
- `.vscode/settings.json`
- `.cursorignore`
- `.copilotignore`

## Avoid by default
- `data/`
- `outputs/`
- `canvases/*.canvas.tsx` unless debugging a specific canvas page
- `web/node_modules/`
- `.venv/`
