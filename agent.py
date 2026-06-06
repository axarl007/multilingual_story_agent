import argparse
import sys

from hooks import post_step_hook, pre_step_hook
from llm_steps import generate_outline, write_story
from observability import TraceCollector, setup_logging
from tools import ProfanityError, apply_profanity_filter, save_story


def run_pipeline(theme: str, age_group: str, language: str = "English") -> None:
    logger = setup_logging()
    collector = TraceCollector()

    logger.info("pipeline_start", extra={"theme": theme, "age_group": age_group, "language": language})

    # Step 1: Generate outline
    span = pre_step_hook("generate_outline", {"theme": theme, "age_group": age_group, "language": language}, logger, collector)
    try:
        outline = generate_outline(theme, age_group, language)
        post_step_hook("generate_outline", {"title": outline.get("title"), "characters": len(outline.get("characters", []))}, span, logger, collector)
    except Exception as e:
        post_step_hook("generate_outline", None, span, logger, collector, error=e)
        collector.write_trace_file(theme, age_group, language)
        raise

    # Step 2: Write story
    span = pre_step_hook("write_story", {"outline_title": outline["title"], "age_group": age_group, "language": language}, logger, collector)
    try:
        story_text = write_story(outline, age_group, language)
        post_step_hook("write_story", {"word_count": len(story_text.split())}, span, logger, collector)
    except Exception as e:
        post_step_hook("write_story", None, span, logger, collector, error=e)
        collector.write_trace_file(theme, age_group, language)
        raise

    # Step 3: Profanity filter
    span = pre_step_hook("apply_profanity_filter", {"word_count": len(story_text.split())}, logger, collector)
    try:
        filter_result = apply_profanity_filter(story_text, language)
        post_step_hook("apply_profanity_filter", filter_result, span, logger, collector)
    except ProfanityError as e:
        post_step_hook("apply_profanity_filter", None, span, logger, collector, error=e)
        collector.write_trace_file(theme, age_group, language)
        raise

    # Step 4: Save story
    span = pre_step_hook("save_story", {"title": outline["title"]}, logger, collector)
    try:
        save_result = save_story(outline["title"], theme, age_group, story_text, language, filter_result["status"])
        post_step_hook("save_story", save_result, span, logger, collector)
    except Exception as e:
        post_step_hook("save_story", None, span, logger, collector, error=e)
        collector.write_trace_file(theme, age_group, language)
        raise

    trace_path = collector.write_trace_file(theme, age_group, language)
    logger.info(
        "pipeline_complete",
        extra={"story": save_result["saved_path"], "trace": str(trace_path)},
    )
    print(f"\nStory saved to: {save_result['saved_path']}")
    print(f"Trace saved to: {trace_path}")
    print(f"\n--- STORY: {outline['title']} ---")
    print(story_text)
    print("--- END STORY ---")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Children's Story Generator Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python agent.py --theme 'amma and baby' --age-group 0-6m\n"
            "  python agent.py --theme animals --age-group 6-12m\n"
            "  python agent.py --theme 'bath time' --age-group 12-18m\n"
            "  python agent.py --theme diwali --age-group 3-5\n"
            "  python agent.py --theme dragons --age-group 6-8\n"
            "  python agent.py --theme 'brave Arjun' --age-group 9-12\n"
            "  python agent.py --theme friendship --age-group 6-8 --language Gujarati\n"
            "  python agent.py --theme diwali --age-group 3-5 --language Hindi\n"
            "  python agent.py --theme 'amma and baby' --age-group 0-6m --language Tamil"
        ),
    )
    parser.add_argument("--theme", required=True, help="Story theme, e.g. 'diwali' or 'animals'")
    parser.add_argument(
        "--age-group",
        required=True,
        choices=["0-6m", "6-12m", "12-18m", "18-24m", "24-36m", "3-5", "6-8", "9-12"],
        metavar="AGE_GROUP",
        help="Target age group: 0-6m, 6-12m, 12-18m, 18-24m, 24-36m (months) or 3-5, 6-8, 9-12 (years)",
    )
    parser.add_argument(
        "--language",
        default="English",
        help="Output language, e.g. 'Gujarati', 'Hindi', 'Tamil'. Default: English",
    )
    args = parser.parse_args()

    try:
        run_pipeline(theme=args.theme, age_group=args.age_group, language=args.language)
    except ProfanityError as e:
        print(f"\nContent Error: {e}", file=sys.stderr)
        print("The generated story contained inappropriate content. Please try a different theme.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
