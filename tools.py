import json
from datetime import datetime, timezone
from pathlib import Path

from better_profanity import profanity

# These words appear naturally in children's stories (fables, nature, adventure)
# but are in better-profanity's default list — whitelist them to avoid false positives.
_CHILDREN_STORY_WHITELIST = [
    "stupid", "fat", "kill", "killed", "kills",
    "naked", "bare", "drunk", "hell", "damn",
    "pot", "pots",  # clay/cooking pots; flagged as drug slang
]
profanity.load_censor_words(whitelist_words=_CHILDREN_STORY_WHITELIST)


class ProfanityError(Exception):
    pass


def apply_profanity_filter(text: str, language: str = "English") -> dict:
    if language.lower() != "english":
        return {"status": "skipped", "reason": f"profanity filter not supported for {language}", "text": text}
    if profanity.contains_profanity(text):
        raise ProfanityError("Profanity detected — pipeline aborted")
    return {"status": "clean", "text": text}


def save_story(title: str, theme: str, age_group: str, story_text: str, language: str = "English", filter_status: str = "clean") -> dict:
    stories_dir = Path("stories")
    stories_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_theme = theme.replace(" ", "_")
    path = stories_dir / f"{ts}_{safe_theme}.json"
    story_data = {
        "title": title,
        "theme": theme,
        "age_group": age_group,
        "language": language,
        "story_text": story_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "filtered_status": filter_status,
    }
    path.write_text(json.dumps(story_data, indent=2, ensure_ascii=False))
    return {"saved_path": str(path), "title": title}
