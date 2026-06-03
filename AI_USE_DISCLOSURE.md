# AI Use Disclosure

## What I Used AI For

This project used AI assistance heavily. AI was a major part of my coding workflow: it helped me implement ideas, iterate on code, run and interpret tests, debug issues, generate local UI pages, and draft documentation. In many cases, AI was the practical coding foundation that let me turn the project concept into a working artifact.

AI also helped surface possible scientific sources. I selected which sources to rely on, checked whether they fit the project, and used them to shape the literature-based score.

## What I Personally Defined

The core project idea and the main design choices came from me. I decided to build an athlete state monitoring system because I wanted better insight into my own training data.

I chose the scoring structure: one literature-based score using published training-load concepts, one personalized score using my own historical percentiles, one learned frontier score using model embeddings, and one integrated score that combines the interpretable and learned signals. I tuned the balance of those equations, chose the reference events used for retrospective checks, collected the Garmin data myself, and decided to use Garmin readiness as the modeling benchmark because it was a meaningful existing target with more background signal than I could create from a single-athlete dataset.

I also chose to use a TCN for the sequence model and directed the UI/page structure. AI sometimes filled in wording or implementation details, but the pages, scoring concepts, evaluation direction, and project framing were things I requested and reviewed.

## Human Collaborators and Sources

There were no other human collaborators.

The code was not built from a forked base repository. External scientific sources used for the literature score are cited in `SCIENTIFIC_RATIONALE.md`.

This is not a clinical or medical model. It is a personal training-analysis project built from private Garmin data.
