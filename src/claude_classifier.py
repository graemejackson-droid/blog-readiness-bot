import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

CLASSIFICATION_PROMPT = """
You are reviewing comments from a blog post Google Doc to determine if any are blocking publication.

Classify each comment as either:
- BLOCKING: explicitly waiting on approval, missing a link or quote, needs sign-off, unresolved factual question, or requires action before publishing
- NON_BLOCKING: editorial notes, suggestions, compliments, resolved context, or general feedback that doesn't require action before publishing

Examples of BLOCKING:
- "Waiting on legal to approve this section"
- "Need the Q2 stat from finance before this goes live"
- "Can you get a quote from the CEO for this?"
- "@Joe can you confirm this is accurate?"
- "TODO: add link here"

Examples of NON_BLOCKING:
- "Nice turn of phrase here"
- "Changed from 'utilize' to 'use'"
- "I restructured this paragraph"
- "Great point!"

Return ONLY a JSON array, no preamble or markdown. Format:
[
  {"comment": "comment text here", "classification": "BLOCKING", "reason": "brief reason"},
  {"comment": "comment text here", "classification": "NON_BLOCKING", "reason": "brief reason"}
]
"""

def classify_comments(comments):
    """
    Takes a list of comment strings and returns classification results.
    Returns a tuple: (has_blocking_comments, classified_list)
    """
    if not comments:
        return False, []

    comments_text = "\n".join([f"- {c}" for c in comments])

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": f"{CLASSIFICATION_PROMPT}\n\nComments to classify:\n{comments_text}"
            }
        ]
    )

    import json
    try:
        raw = message.content[0].text.strip()
        classified = json.loads(raw)
        has_blocking = any(c["classification"] == "BLOCKING" for c in classified)
        return has_blocking, classified
    except (json.JSONDecodeError, IndexError, KeyError):
        # If parsing fails, treat as blocking to be safe
        return True, []
