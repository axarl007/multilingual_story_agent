import asyncio
import json
import re
from typing import Any

from claude_code_sdk import query, ClaudeCodeOptions, AssistantMessage, SystemMessage, TextBlock
from claude_code_sdk._errors import MessageParseError
from claude_code_sdk._internal import client as _client

# The claude binary (v2.1.x+) emits "rate_limit_event" which SDK 0.0.25 doesn't know.
# client.py binds parse_message locally via "from .message_parser import parse_message",
# so we patch the binding inside the client module directly.
_original_parse = _client.parse_message


def _tolerant_parse(data: dict) -> Any:
    try:
        return _original_parse(data)
    except MessageParseError as exc:
        if "Unknown message type" in str(exc):
            return SystemMessage(subtype=data.get("type", "unknown"), data=data)
        raise


_client.parse_message = _tolerant_parse


async def _claude_call(prompt: str, system: str) -> str:
    """Single-turn text call to Claude via claude-code-sdk. Returns the full text response."""
    options = ClaudeCodeOptions(
        max_turns=1,
        system_prompt=system,
        extra_args={"tools": ""},   # --tools "" disables all Claude Code built-in tools
    )
    text_parts: list[str] = []
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
    return "".join(text_parts).strip()


def _run(coro: Any) -> Any:
    """Run a coroutine from synchronous CLI code."""
    return asyncio.run(coro)


# Fix 4: Language tiers — Tier 2 languages get additional prompting scaffolding.
# Tier 1: high training data, Claude generates natively.
# Tier 2: moderate data, needs explicit register guidance to avoid Hindi/English calques.
_TIER1_LANGUAGES = {"english", "hindi", "bengali", "tamil", "urdu"}
_TIER2_LANGUAGES = {"gujarati", "marathi", "telugu", "kannada", "malayalam", "punjabi", "odia"}


def _language_tier(language: str) -> int:
    lang = language.lower()
    if lang in _TIER1_LANGUAGES:
        return 1
    if lang in _TIER2_LANGUAGES:
        return 2
    return 2  # unknown languages treated as Tier 2


def generate_outline(theme: str, age_group: str, language: str = "English") -> dict:
    """
    Calls Claude to produce a story outline as JSON.
    Returns: {title: str, characters: list[str], plot_points: list[str]}
    Raises ValueError if the response is malformed or missing required fields.
    """
    # Fix 1: Specify plot_points language so the entire outline is seeded in the target
    # language — prevents mixed-language outline (GU title + EN plot_points) that causes
    # the model to translate rather than think natively when writing the story.
    lang_instruction = (
        f"Generate the title, all character names, and all plot points in {language}. "
        if language.lower() != "english"
        else ""
    )
    system = (
        "You are a children's story outline generator for an Indian audience. "
        "Weave in Indian cultural context where it fits the story naturally — "
        "Indian names, animals, settings, foods, and festivals — "
        "but only include elements that genuinely serve the narrative. "
        f"{lang_instruction}"
        "Respond ONLY with a valid JSON object. "
        "Do not include markdown code fences, explanations, or any text outside the JSON."
    )
    prompt = (
        f"Create a short children's story outline.\n"
        f"Theme: {theme}\n"
        f"Age group: {age_group}\n\n"
        f"Return exactly this JSON structure with your content filled in:\n"
        f'{{"title": "story title here", '
        f'"characters": ["character name 1", "character name 2"], '
        f'"plot_points": ["plot point 1", "plot point 2", "plot point 3"]}}'
    )

    raw = _run(_claude_call(prompt, system))

    if not raw:
        raise ValueError("Empty response from LLM when generating outline")

    # Strip any accidental markdown fences
    json_str = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()

    try:
        outline = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON for outline: {e}\nRaw response: {raw[:200]}") from e

    if not outline.get("title"):
        raise ValueError("Outline missing required field 'title'")
    if not outline.get("characters"):
        raise ValueError("Outline missing required field 'characters'")
    if len(outline.get("plot_points", [])) < 3:
        raise ValueError("Outline requires at least 3 plot_points")

    return outline


def write_story(outline: dict, age_group: str, language: str = "English") -> str:
    """
    Calls Claude to write the full story given an outline dict.
    Returns the story text as a plain string.
    """
    age_guidance = {
        "0-6m": (
            "babies 0-6 months old. Use 20-40 words total. Write 4-8 short rhyming lines "
            "with a gentle, comforting theme (e.g., Amma's love, baby's bedtime, the moon). "
            "Each line must be 1-3 words only. Use familiar Indian words: Amma, Nanu, Chanda "
            "(moon), soft sounds. The lines should feel connected — not random — with a warm, "
            "reassuring feeling throughout. End with a calming, sleepy line."
        ),
        "6-12m": (
            "babies 6-12 months old. Use 50-100 words total. Use a repetitive sentence pattern "
            "where each sentence follows the same structure with one word changing "
            "(e.g., 'See the cow. See the elephant. See the parrot.'). "
            "The pattern should build toward a simple satisfying conclusion "
            "(all animals are named, everyone says goodnight, the ball is found). "
            "Include 1-2 questions like 'Where is the cow?' to invite caregiver interaction. "
            "Use Indian animals, names, and settings. Sentences: 2-4 words, present tense only."
        ),
        "12-18m": (
            "toddlers 12-18 months old. Use 100-150 words total. Use a repeating pattern with "
            "a simple cause-and-effect pair per moment (e.g., 'Raju jumped. He splashed.'). "
            "The story should have a simple warm resolution or moral (e.g., helping is good, "
            "sharing makes friends happy). Vocabulary: concrete nouns and action verbs, a few "
            "early adjectives (big, little, hot, cold). Sentences: 2-6 words, present tense. "
            "Use Indian names, animals (cow, elephant, peacock), and daily life (chai, dosa, "
            "mango). Include 1-2 participation prompts ('What does the cow say?')."
        ),
        "18-24m": (
            "toddlers 18-24 months old. Use 150-250 words total. Include a simple cause-and-effect "
            "chain and one clear problem-resolution with a simple message (e.g., helping a friend, "
            "being brave, kindness). Include a short repeated refrain the child can anticipate. "
            "Vocabulary: nouns, action verbs, early adjectives, simple prepositions (in, on, under). "
            "Sentences: 3-8 words. Use Indian names, settings (mango tree, village well, festival), "
            "animals, and foods (idli, kheer). Simple compound sentences with 'and' are fine."
        ),
        "24-36m": (
            "toddlers 24-36 months old. Use 250-400 words total. Include a clear beginning-middle-end "
            "with one simple conflict, resolution, and a meaningful lesson (sharing, courage, kindness, "
            "honesty). Use a repeated refrain. Include simple dialogue. "
            "Vocabulary: nouns, verbs, adjectives, adverbs (quickly, slowly, softly), "
            "time words (first, then, next), emotional vocabulary (proud, scared, excited). "
            "Sentences: 4-12 words. Set in an Indian context: Indian names, festivals (Diwali, Holi), "
            "animals, foods, and family relationships (Dadi, Nana, Amma, Appa)."
        ),
        "3-5": (
            "children 3-5 years old. Use approximately 150-200 words. Very simple sentences and "
            "easy vocabulary. Include an Indian setting, Indian character names, and familiar "
            "Indian cultural elements (festivals, foods, animals, family). Simple moral or message."
        ),
        "6-8": (
            "children 6-8 years old. Use approximately 300-400 words. Simple vocabulary, short "
            "paragraphs. Set in an Indian context with Indian names, cultural details, and "
            "relatable Indian family or community life. Include a clear moral or lesson."
        ),
        "9-12": (
            "children 9-12 years old. Use approximately 600-800 words. Richer vocabulary and "
            "descriptive language. Full narrative arc set in India with vivid cultural details, "
            "Indian mythology references if appropriate, and a meaningful theme."
        ),
    }[age_group]

    if language.lower() == "english":
        language_instruction = ""
    elif _language_tier(language) == 1:
        # Fix 2 (Tier 1): Strong language capability — script enforcement is sufficient.
        language_instruction = (
            f"Write the entire story in {language}. Use {language} script throughout. "
        )
    else:
        # Fix 2 (Tier 2): Weaker training data — add native register guidance to prevent
        # the model from translating Hindi/English vocabulary into the target script.
        language_instruction = (
            f"Write the entire story in {language}. Use {language} script throughout. "
            f"Use vocabulary and phrasing that a native {language}-speaking grandparent "
            f"would use naturally with a small child — do not translate from Hindi or English. "
            f"Choose words by how they feel in {language}, not by what they mean in another language. "
        )

    system = (
        f"You are a creative children's story writer for an Indian audience. "
        f"Write {age_guidance}. "
        # Fix 3: Cultural elements are narrative-optional, not mandatory — prevents the model
        # from force-inserting animals/settings that have no story function.
        f"Weave in Indian cultural context where it fits the story naturally — Indian names, "
        f"settings, animals, foods, and festivals — but only include elements that genuinely "
        f"serve the narrative. Do not insert cultural details that don't earn their place. "
        f"{language_instruction}"
        f"Return ONLY the story text. No title header, no author note, no markdown — just the story."
    )
    prompt = (
        f"Write a children's story based on this outline:\n"
        f"{json.dumps(outline, indent=2)}\n\n"
        f"Write a complete, engaging, age-appropriate piece for the {age_group} age band. "
        f"Keep the language clean and suitable for children."
    )

    story = _run(_claude_call(prompt, system))

    if not story:
        raise ValueError("Empty response from LLM when writing story")

    return story
