Generate a children's short story using the story agent in this project.
All stories are set in an **Indian cultural context** (Indian names, animals, foods, settings, festivals).
Stories can be generated in English or any major Indian language.

**Arguments:** $ARGUMENTS

**How to parse:** The format is `<theme> [language] <age-group>`
- Age-group: the **last token** — must be one of the valid values below (e.g. `6-8`, `3-5`, `0-6m`)
- Language (optional): the **second-to-last token** IF it matches a known language name below; otherwise it is part of the theme
- Theme: everything remaining before the language (or before age-group if no language given)
- If age-group is missing or invalid, default to `6-8` and mention it
- If language is missing, default to `English`

**Valid languages:** English, Gujarati, Hindi, Tamil, Bengali, Marathi, Telugu, Kannada, Malayalam, Punjabi, Odia

**Valid age groups:**
- Months (infant/toddler): `0-6m`, `6-12m`, `12-18m`, `18-24m`, `24-36m`
- Years (child): `3-5`, `6-8`, `9-12`

**Examples:**
- `amma and baby 0-6m` → theme=amma and baby, language=English, age_group=0-6m
- `diwali Gujarati 3-5` → theme=diwali, language=Gujarati, age_group=3-5
- `friendship Hindi 6-8` → theme=friendship, language=Hindi, age_group=6-8
- `brave Arjun Tamil 9-12` → theme=brave Arjun, language=Tamil, age_group=9-12
- `dragons 6-8` → theme=dragons, language=English, age_group=6-8
- `friendship` (no age group) → theme=friendship, language=English, age_group=6-8 (default)

**Steps:**
1. Parse theme, language, and age_group from the arguments above
2. Run the story agent (use the Bash tool):
   ```
   python agent.py --theme "<theme>" --age-group "<age-group>" --language "<language>"
   ```
3. In the output, find the block between `--- STORY: <title> ---` and `--- END STORY ---`
4. Present the story to the user with the **title as a heading** and the story text below
5. On a separate line, note the language used and where the file was saved (look for `Story saved to:` in the output)
