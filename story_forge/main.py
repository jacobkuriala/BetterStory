"""Entry point for story_forge — CLI and main Creator/Reviewer loop."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure stdout/stderr handle Unicode on Windows (cp1252 can't encode LLM output)
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

import anthropic
from dotenv import load_dotenv

from story_forge.config import MAX_ITERATIONS, SCORE_THRESHOLD
from story_forge.agents.creator import generate_rubric, create_story
from story_forge.agents.reviewer import review_story


def _get_user_inputs() -> tuple[str, bool]:
    """Collect the story brief and steering preference from the user."""
    print("=" * 60)
    print("  STORY FORGE — Iterative Creative Writing Engine")
    print("=" * 60)
    print()

    print("Enter your story brief (theme, style, tone, audience, length, etc.).")
    print("When finished, enter a blank line:")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    brief = "\n".join(lines).strip()

    if not brief:
        print("Error: Brief cannot be empty.")
        sys.exit(1)

    steering_input = input("\nEnable steering between iterations? (y/n): ").strip().lower()
    steerable = steering_input == "y"
    print()
    return brief, steerable


def _print_scores_table(scores: dict[str, int], average: float) -> None:
    """Print scores as a formatted table."""
    max_name_len = max(len(name) for name in scores)
    print(f"\n  {'Dimension':<{max_name_len}}  Score")
    print(f"  {'-' * max_name_len}  -----")
    for name, score in scores.items():
        print(f"  {name:<{max_name_len}}  {score:>5}")
    print(f"  {'-' * max_name_len}  -----")
    print(f"  {'Average':<{max_name_len}}  {average:>5.1f}")
    print()


def _save_output(
    brief: str,
    final_story: str,
    history: list[dict],
) -> str:
    """Save the full session to a markdown file. Returns the file path."""
    outputs_dir = Path(__file__).resolve().parent / "outputs"
    outputs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filepath = outputs_dir / f"story_{timestamp}.md"

    lines = [
        "# Story Forge Output\n",
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n",
        "## Original Brief\n",
        f"{brief}\n",
        "## Final Story\n",
        f"{final_story}\n",
        "## Iteration History\n",
    ]

    for entry in history:
        lines.append(f"### Iteration {entry['iteration']}\n")
        lines.append(f"#### Draft\n\n{entry['story']}\n")
        lines.append(f"#### Scores\n")
        for dim, score in entry["scores"].items():
            lines.append(f"- **{dim}**: {score}")
        lines.append(f"- **Average**: {entry['average']:.1f}\n")
        lines.append(f"#### Feedback\n\n{entry['feedback']}\n")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return str(filepath)


def run(
    client: anthropic.Anthropic | None = None,
    brief: str | None = None,
    steerable: bool | None = None,
) -> None:
    """Main loop. Parameters allow injection for testing."""
    load_dotenv()

    if client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY not found. Create a .env file (see .env.example).")
            sys.exit(1)
        client = anthropic.Anthropic(api_key=api_key)

    if brief is None or steerable is None:
        brief, steerable = _get_user_inputs()

    # Step 1: Generate rubric
    print("Generating scoring rubric from your brief...")
    rubric = generate_rubric(client, brief)
    print(f"Rubric dimensions: {', '.join(d['name'] for d in rubric)}\n")

    # Main loop
    history: list[dict] = []
    feedback: str | None = None
    final_story = ""

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"{'=' * 60}")
        print(f"  === Iteration {iteration}/{MAX_ITERATIONS} ===")
        print(f"{'=' * 60}\n")

        # Step 2: Create/revise story
        print("Creator is writing..." if iteration == 1 else "Creator is revising...")
        story = create_story(client, brief, feedback)
        final_story = story
        print(f"\n--- Story ---\n\n{story}\n\n--- End Story ---\n")

        # Step 3: Review
        print("Reviewer is scoring...")
        review = review_story(client, brief, rubric, story)

        scores = review["scores"]
        average = review["average"]
        satisfied = review["satisfied"]
        review_feedback = review["feedback"]

        _print_scores_table(scores, average)
        print(f"Satisfied: {satisfied}\n")
        print(f"Feedback:\n{review_feedback}\n")

        history.append({
            "iteration": iteration,
            "story": story,
            "scores": scores,
            "average": average,
            "satisfied": satisfied,
            "feedback": review_feedback,
        })

        # Check exit condition
        if average >= SCORE_THRESHOLD and satisfied:
            print(f"Quality threshold reached at iteration {iteration}!")
            break

        if iteration == MAX_ITERATIONS:
            print(f"Maximum iterations ({MAX_ITERATIONS}) reached.")
            break

        # Step 4: Steering
        feedback = review_feedback
        if steerable:
            steering = input("Add steering input (or press Enter to skip): ").strip()
            if steering:
                feedback = f"{review_feedback}\n\nAdditional direction from the author:\n{steering}"
            print()

    # Save and print summary
    filepath = _save_output(brief, final_story, history)

    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Total iterations: {len(history)}")
    if history:
        final = history[-1]
        _print_scores_table(final["scores"], final["average"])
    print(f"  Saved to: {filepath}")
    print()


def main() -> None:
    """CLI entry point."""
    try:
        run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)
    except anthropic.APIError as e:
        print(f"\nFatal API error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
