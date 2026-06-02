# Quick Start: Coaching Agent

## 30-Second Setup

```bash
cd /Users/callumsherry/athlete-state-model

# Demo mode (no API key needed)
python scripts/run_coaching_agent.py --demo

# Or show comprehensive demo
python scripts/demo_agent_queries.py
```

## Interactive Mode

```bash
export OPENROUTER_API_KEY="sk-or-..."
python scripts/run_coaching_agent.py
```

Then ask questions like:
```
You: Why was May 15 flagged at 72 km?
You: Compare my bone stress in spring 2024 vs now.
You: What if I'd cut volume by 15%?
```

## What You Get

- **Tool grounding:** Every answer comes from your data
- **Auditable:** See exactly which tools were called
- **Demo-ready:** Works offline or with OpenRouter
- **3 killer questions:** Tested and optimized

## Files Created

| File | Purpose |
|------|---------|
| `src/agent_tools.py` | Tool definitions (get_day, compare_days, etc.) |
| `scripts/run_coaching_agent.py` | Main agent + OpenRouter integration |
| `scripts/demo_agent_queries.py` | Standalone demo script |
| `scripts/test_agent.py` | Tool validation |
| `scripts/test_openrouter.py` | API connection test |
| `README_AGENT.md` | Full documentation |
| `AGENT_IMPLEMENTATION.md` | Build summary |

## How It Works

```
User Question
    ↓
OpenRouter LLM (with tool definitions)
    ↓
LLM decides: Which tools to call?
    ↓
Tools execute (read from CSV/JSON)
    ↓
LLM synthesizes answer from tool results
    ↓
Grounded, auditable response
```

## Next Steps

**Week 1 (Now):** ✅ Agent ready
**Week 2:** Build evaluation canvas
**Week 3:** Create pitch slide with live demo
**Weeks 4–9:** Polish and integrate

---

Ready to demo? Run one of the commands above.
