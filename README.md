# BetterStory — Story Forge

A two-agent creative writing engine that iteratively refines stories using Claude. A **Creator** agent writes the story, a **Reviewer** agent scores and critiques it, and they loop until the quality threshold is met.

## How it works

1. You provide a story brief (theme, style, tone, audience, length).
2. The Creator generates a scoring rubric tailored to your brief.
3. The Creator writes a first draft.
4. The Reviewer scores it on each rubric dimension (1–10) and gives detailed feedback.
5. The Creator revises based on the feedback.
6. Steps 4–5 repeat until the average score reaches 8.0+ or 15 iterations are exhausted.
7. The final story and full iteration history are saved to a markdown file.

Optionally, you can enable **steering** to inject your own guidance between iterations.

## Setup

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

```bash
# Clone the repo
git clone https://github.com/jacobkuriala/BetterStory.git
cd BetterStory

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Usage

```bash
python -m story_forge.main
```

You'll be prompted to:
1. Enter your story brief (end with a blank line).
2. Choose whether to enable steering (`y`/`n`).

The app will then iterate, printing each draft, scores, and feedback to the console. When finished, it saves everything to `story_forge/outputs/story_<timestamp>.md`.

## Configuration

Edit `story_forge/config.py` to adjust:

| Constant | Default | Description |
|---|---|---|
| `MAX_ITERATIONS` | 15 | Maximum Creator/Reviewer loops |
| `SCORE_THRESHOLD` | 8.0 | Average score needed to stop |
| `CREATOR_MODEL` | `claude-opus-4-5` | Model for the Creator agent |
| `REVIEWER_MODEL` | `claude-sonnet-4-5` | Model for the Reviewer agent |

## Running tests

```bash
pytest tests/ -v
```

## Project structure

```
story_forge/
  main.py               # Entry point, CLI, main loop
  config.py             # Constants: models, thresholds, limits
  agents/
    creator.py          # Creator agent (rubric + story generation)
    reviewer.py         # Reviewer agent (scoring + feedback)
  prompts/
    creator.md          # Creator system prompt
    reviewer.md         # Reviewer system prompt
  outputs/              # Saved stories (auto-created)
```
