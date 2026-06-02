"""Generate static coaching Q&A examples for the demo canvas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


EXAMPLES: list[dict[str, Any]] = [
    {
        "question": "Why is May 15 still a watch day if this week is lower than my peak weeks?",
        "answer": (
            "May 15 is not being treated like a peak-volume danger day. The alert is watch because the accumulated "
            "state is still high after the prior load block, even though the latest 7-day running volume has eased.\n\n"
            "The practical read is: do not chase another build immediately. Hold volume steady or take a lighter week "
            "until the accumulated state drops, then progress again."
        ),
        "evidence": [
            ["Date", "2026-05-15"],
            ["Alert", "Watch"],
            ["Integrated score", "58.63"],
            ["7-day running", "71.5 km"],
            ["28-day running", "362.2 km"],
            ["Accumulated state", "70.05"],
        ],
    },
    {
        "question": "What was different about the spring 2024 bone-stress build-up?",
        "answer": (
            "The spring 2024 block had agreement across the load rules, the personalized history, and the accumulated "
            "frontier state before the injury endpoint. That matters because it was not just one unusual signal; the "
            "independent tracks converged.\n\n"
            "The useful coaching takeaway is to treat all-track agreement as a stronger warning than a single moderate "
            "flag. When that happens during a running ramp, the safer move is a real down week rather than a small trim."
        ),
        "evidence": [
            ["Reference", "Bone stress injury, spring 2024"],
            ["First literature high lead", "56 days"],
            ["First frontier high lead", "50 days"],
            ["All-track agreement", "2024-02-09"],
            ["Agreement lead", "52 days"],
        ],
    },
    {
        "question": "How should I interpret frontier high when literature is not high?",
        "answer": (
            "That pattern means the learned-state signal is elevated while the simple running-load rules are not. It is "
            "not proof of injury risk by itself, but it is a prompt to look for hidden strain: recovery response, unusual "
            "multi-sport load, similarity to prior concerning states, or negative readiness surprise.\n\n"
            "The right action is investigation, not panic. Check the day details, recent trend, and recovery context before "
            "deciding whether to reduce training."
        ),
        "evidence": [
            ["Pattern", "Frontier high, literature not"],
            ["Full-history count", "172 days"],
            ["Frontier score shown", "Accumulated frontier state"],
            ["Best use", "Investigate hidden strain"],
        ],
    },
    {
        "question": "What should I change this week if the current reason is sustained high running volume?",
        "answer": (
            "The answer should focus on reducing accumulated load, not just avoiding one hard session. If the last month "
            "is still heavy, a few easier days may not be enough to move the state.\n\n"
            "A conservative week would cut total running volume, keep intensity low, and avoid stacking long or hard days. "
            "The goal is to let the accumulated state fall before starting the next build."
        ),
        "evidence": [
            ["Current reason example", "Sustained high running volume"],
            ["Recent 28-day load", "High"],
            ["Recommended action", "Recovery-oriented week"],
            ["Progression rule", "Restart gradually after state drops"],
        ],
    },
]


def render_canvas(examples: list[dict[str, Any]]) -> str:
    data = json.dumps({"examples": examples}, indent=2)
    return f"""import {{
  Callout,
  Card,
  CardBody,
  CardHeader,
  H1,
  H2,
  Stack,
  Table,
  Text,
}} from 'cursor/canvas';

const payload = {data} as const;

function AnswerText({{ content }}: {{ content: string }}) {{
  return (
    <Stack gap={{8}}>
      {{content.split('\\n\\n').map((paragraph, idx) => (
        <Text key={{idx}}>{{paragraph}}</Text>
      ))}}
    </Stack>
  );
}}

export default function CoachingQa() {{
  return (
    <Stack gap={{20}}>
      <Stack gap={{8}}>
        <H1>Coaching Q&amp;A Examples</H1>
        <Text>
          Example questions and answers for the coaching page.
        </Text>
      </Stack>

      <Callout tone="info" title="How to read these">
        These are static examples of the answer style: short, grounded in local monitoring data, and framed as training
        decisions rather than diagnosis.
      </Callout>

      {{payload.examples.map((example, index) => (
        <Card key={{example.question}}>
          <CardHeader>{{index + 1}}. {{example.question}}</CardHeader>
          <CardBody>
            <Stack gap={{14}}>
              <AnswerText content={{example.answer}} />
              <H2>Grounding</H2>
              <Table headers={{['Signal', 'Value']}} rows={{example.evidence}} striped />
            </Stack>
          </CardBody>
        </Card>
      ))}}
    </Stack>
  );
}}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate static coaching Q&A examples.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analysis"))
    parser.add_argument("--canvas-dir", type=Path, default=REPO_ROOT / "canvases")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "coaching_qa.json").write_text(json.dumps({"examples": EXAMPLES}, indent=2), encoding="utf-8")
    args.canvas_dir.mkdir(parents=True, exist_ok=True)
    (args.canvas_dir / "coaching-qa.canvas.tsx").write_text(render_canvas(EXAMPLES), encoding="utf-8")
    print(f"Wrote coaching Q&A examples ({len(EXAMPLES)} examples)")


if __name__ == "__main__":
    main()
