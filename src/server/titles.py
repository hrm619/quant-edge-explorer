"""Haiku-based conversation title generation."""

from __future__ import annotations

import anthropic

TITLE_PROMPT = """Given this opening exchange from a research conversation about
NFL fantasy football data analysis, generate a concise title (5-8 words, no
quotes, no punctuation at the end).

User: {user_message}
Assistant: {assistant_summary}

Title:"""

TITLE_MODEL = "claude-haiku-4-5-20251001"


def generate_title(
    client: anthropic.Anthropic,
    user_message: str,
    assistant_summary: str,
) -> str:
    """Generate a short conversation title via Haiku."""
    prompt = TITLE_PROMPT.format(
        user_message=user_message[:500],
        assistant_summary=assistant_summary[:500],
    )

    response = client.messages.create(
        model=TITLE_MODEL,
        max_tokens=30,
        messages=[{"role": "user", "content": prompt}],
    )

    title = ""
    for block in response.content:
        if hasattr(block, "text"):
            title += block.text

    return title.strip().strip('"').strip(".")[:100]
