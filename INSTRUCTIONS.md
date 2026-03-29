# BetterStory — Project Instructions

> Build a Python console application called `story_forge` that uses a two-agent loop to iteratively refine a piece of creative writing.

---

## Overview

The user provides a story brief and configuration. A **Creator** agent writes the story. A **Reviewer** agent scores it and gives feedback. They loop until quality is high enough or the iteration limit is hit. The final story is printed and saved to a file.

---

## Project structure

```
story_forge/
  main.py               # entry point, CLI, main loop
  agents/
    creator.py          # Creator agent logic
    reviewer.py         # Reviewer agent logic
  prompts/
    creator.md          # Creator system prompt
    reviewer.md         # Reviewer system prompt
  outputs/              # saved stories go here (auto-created)
  config.py             # constants: max iterations, score threshold, models
  requirements.txt
```

---

## User inputs (collected at startup via console prompts)

- `brief`: free-text story requirements (theme, style, tone, audience, length, etc.)
- `steerable`: boolean — ask the user "Enable steering between iterations? (y/n)"

---

## Models

- Creator: `claude-opus-4-5` (all creative and interpretive work)
- Reviewer: `claude-sonnet-4-5`
- Use the Anthropic Python SDK with standard (non-streaming) calls for simplicity

---

## Loop logic

1. **Rubric generation (Creator, once at the start):** The Creator reads the user's brief and produces a structured JSON rubric — a list of 4–6 named scoring dimensions relevant to *this specific brief* (e.g. `allegorical_clarity`, `prose_accessibility`, `character_voice`). This rubric is stored internally and passed to the Reviewer each round. The Creator never sees the rubric again after this step.

2. **Story creation (Creator):** On the first iteration, write the story from the brief alone. On subsequent iterations, write a revised story using the brief + the Reviewer's plain-text feedback only. Do not pass scores or the rubric to the Creator — only the narrative critique.

3. **Review (Reviewer):** Given the brief, the rubric, and the current story, the Reviewer returns a structured JSON response:
   ```json
   {
     "scores": { "dimension_name": <1-10>, ... },
     "average": <float>,
     "satisfied": <bool>,
     "feedback": "<targeted narrative critique for the Creator>"
   }
   ```
   `satisfied` should be true when `average >= 8.0`. The feedback field should be rich and specific — not just "improve the pacing" but *how* and *where*.

4. **Steering (if `steerable = true`):** After printing the Reviewer's feedback and scores, prompt the user: `"Add steering input (or press Enter to skip): "`. If the user types something, append it to the feedback passed to the Creator next round.

5. **Loop until:** `average >= 8.0` AND `satisfied == true`, OR 15 iterations reached.

---

## Console output (each iteration)

Print clearly labelled sections:
- `=== Iteration N/15 ===`
- The full story text
- Scores per dimension + average (formatted as a small table)
- Reviewer feedback
- Steering prompt (if enabled)

At the end, print a summary: total iterations, final scores, and the path to the saved file.

---

## Output file

Save to `outputs/story_<timestamp>.md`. The file should contain:
- The user's original brief
- The final story
- The full iteration history (each draft + scores + feedback)

---

## Prompts (in `prompts/creator.md` and `prompts/reviewer.md`)

Write thoughtful, detailed system prompts for each agent. The Creator's prompt should emphasise taking feedback seriously and producing genuinely revised work — not surface edits. The Reviewer's prompt should emphasise honest, calibrated scoring (don't inflate scores; 8+ should mean genuinely excellent work that fulfils the brief), and feedback that is specific enough to act on. Keep application logic out of the prompt files.

---

## Error handling

Handle API errors gracefully — print the error and retry the failed call once before aborting. Validate that the Reviewer's JSON response is parseable; if not, ask it to try again once.

---

## Dependencies

`anthropic`, `python-dotenv`. Read the API key from a `.env` file (`ANTHROPIC_API_KEY`). Include a `.env.example`. Add a clear `README.md` with setup and usage instructions.
