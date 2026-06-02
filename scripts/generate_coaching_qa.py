"""Generate grounded coaching Q&A for recent flagged monitoring days."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def load_local_env() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()

import pandas as pd

from src.coaching_qa import generate_coaching_entries


def sanitize_for_json(value: object) -> object:
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, dict):
        return {key: sanitize_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_for_json(item) for item in value]
    return value


def render_canvas(entries: list[dict[str, object]], model: str) -> str:
    data = json.dumps({"model": model, "entries": sanitize_for_json(entries)}, indent=2)
    return f"""import {{
  Callout,
  CollapsibleSection,
  H1,
  H2,
  H3,
  Stack,
  Table,
  Text,
}} from 'cursor/canvas';

const payload = {data} as const;

function AnswerText({{ content }}: {{ content: string }}) {{
  const lines = content.split('\\n');
  return (
    <Stack gap={{6}}>
      {{lines.map((line, idx) => {{
        const trimmed = line.trim();
        if (!trimmed) return null;
        if (trimmed.startsWith('### ')) {{
          return <H3 key={{idx}}>{{trimmed.slice(4)}}</H3>;
        }}
        if (trimmed.startsWith('- ')) {{
          return <Text key={{idx}}>• {{trimmed.slice(2)}}</Text>;
        }}
        if (trimmed.startsWith('**') && trimmed.includes('**', 2)) {{
          const end = trimmed.indexOf('**', 2);
          const bold = trimmed.slice(2, end);
          const rest = trimmed.slice(end + 2).replace(/^:\\s*/, '');
          return (
            <Text key={{idx}} weight="semibold">
              {{bold}}{{rest ? `: ${{rest}}` : ''}}
            </Text>
          );
        }}
        return <Text key={{idx}}>{{trimmed}}</Text>;
      }})}}
    </Stack>
  );
}}

export default function CoachingQa() {{
  const latest = payload.entries[0];

  return (
    <Stack gap={{20}}>
      <Stack gap={{8}}>
        <H1>Coaching Q&amp;A</H1>
        <Text>
          Grounded answers for recent flagged days — generated from structured scores, attribution, and scientific rationale.
        </Text>
        <Text tone="secondary" size="small">
          Model: {{payload.model}} · requires OPENROUTER_API_KEY · regenerate with generate_coaching_qa.py
        </Text>
      </Stack>

      {{latest && latest.status === 'ok' ? (
        <Callout tone="info" title={{`${{latest.date}} · ${{String(latest.tier).replace(/_/g, ' ')}} · ${{String(latest.agreement).replace(/_/g, ' ')}}`}}>
          <AnswerText content={{latest.answer_markdown || ''}} />
        </Callout>
      ) : (
        <Callout tone="warning" title="No coaching answer yet">
          {{latest?.error || 'Set OPENROUTER_API_KEY and rerun generate_coaching_qa.py.'}}
        </Callout>
      )}}

      <H2>Recent flagged days</H2>
      <Table
        headers={{['Date', 'Tier', 'Agreement', 'Status']}}
        rows={{payload.entries.map((entry) => [
          entry.date,
          String(entry.tier).replace(/_/g, ' '),
          String(entry.agreement).replace(/_/g, ' '),
          entry.status,
        ])}}
        striped
      />

      <CollapsibleSection title="All answers" count={{payload.entries.length}}>
        <Stack gap={{16}}>
          {{payload.entries.map((entry) => (
            <Stack key={{entry.date}} gap={{8}}>
              <H2>{{entry.date}} · {{String(entry.tier).replace(/_/g, ' ')}}</H2>
              {{entry.status === 'ok' ? (
                <AnswerText content={{entry.answer_markdown || ''}} />
              ) : (
                <Text tone="secondary">{{entry.error || 'No answer generated.'}}</Text>
              )}}
            </Stack>
          ))}}
        </Stack>
      </CollapsibleSection>
    </Stack>
  );
}}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OpenRouter coaching Q&A for flagged days.")
    parser.add_argument("--scores", type=Path, default=Path("outputs/analysis/athlete_bone_stress_scores.csv"))
    parser.add_argument("--periods", type=Path, default=Path("outputs/analysis/athlete_bone_stress_periods.csv"))
    parser.add_argument("--rationale", type=Path, default=Path("SCIENTIFIC_RATIONALE.md"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analysis"))
    parser.add_argument(
        "--canvas-dir",
        type=Path,
        default=REPO_ROOT / "canvases",
    )
    parser.add_argument("--model", type=str, default="anthropic/claude-3.5-haiku")
    parser.add_argument("--recent-days", type=int, default=14)
    parser.add_argument("--max-entries", type=int, default=5)
    parser.add_argument("--skip-llm", action="store_true", help="Write placeholder canvas without calling OpenRouter.")
    args = parser.parse_args()

    scores = pd.read_csv(args.scores, parse_dates=["date"])
    periods = pd.read_csv(args.periods, parse_dates=["start_date", "end_date"]) if args.periods.exists() else pd.DataFrame()

    if args.skip_llm:
        candidates = scores.sort_values("date", ascending=False).head(args.max_entries)
        entries = [
            {
                "date": str(row["date"].date()),
                "tier": row.get("operational_alert_tier"),
                "agreement": row.get("monitoring_signal_agreement"),
                "context": {},
                "answer_markdown": None,
                "status": "skipped",
                "error": "LLM skipped (--skip-llm). Set OPENROUTER_API_KEY and rerun.",
            }
            for _, row in candidates.iterrows()
        ]
    else:
        entries = generate_coaching_entries(
            scores,
            periods,
            args.rationale,
            model=args.model,
            recent_days=args.recent_days,
            max_entries=args.max_entries,
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "coaching_qa.json").write_text(json.dumps({"model": args.model, "entries": entries}, indent=2), encoding="utf-8")
    args.canvas_dir.mkdir(parents=True, exist_ok=True)
    (args.canvas_dir / "coaching-qa.canvas.tsx").write_text(render_canvas(entries, args.model), encoding="utf-8")
    print(f"Wrote coaching Q&A ({len(entries)} entries)")


if __name__ == "__main__":
    main()
