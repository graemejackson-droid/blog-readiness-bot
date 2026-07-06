import requests
from config import SHORTCUT_API_TOKEN

BASE_URL = "https://api.app.shortcut.com/api/v3"

HEADERS = {
    "Content-Type": "application/json",
    "Shortcut-Token": SHORTCUT_API_TOKEN
}

BLOG_PREFIXES = (
    "[blog]",
    "[blog post]",
    "[content]",
    "[design]"
)

# State IDs for "In Progress" and "Needs Verification" across all workflows
BLOG_STATE_IDS = (
    500000015,   # Default: In Progress
    500006100,   # Default: Needs Verification
    500312330,   # Experiment: Development
    500312332,   # Experiment: Needs Verification
    500315599,   # Simplified: In Process
    500317381,   # Fanatics: In Progress
    500317382,   # Fanatics: Needs Verification
    500330893,   # Basketball: In Progress
    500330894,   # Basketball: QA Testing
    500331212,   # A-Team: In Progress
    500331214,   # A-Team: Needs Verification
    500331414,   # App Platform: In Progress
    500334421,   # Insights Hub: In Process
    500334423,   # Insights Hub: Ready For Review
    500389406,   # CV Platform Team: In Progress
    500389407,   # CV Platform Team: Needs Verification
    500390431,   # Snowplow: Analytics In Progress
    500390428,   # Snowplow: Engineering In Progress
    500391935,   # Analytics Team: In Development
    500391936,   # Analytics Team: Ready for Review
    500406321,   # AI Enablement: In Progress
    500406323,   # AI Enablement: Needs Verification
)


def search_stories_by_prefix(prefix):
    """
    Search Shortcut for stories matching a blog prefix using quoted title search.
    Filters by workflow state ID in Python after fetching.
    Paginates through all results.
    """
    url = f"{BASE_URL}/search/stories"
    stories = []
    next_cursor = None

    # Use quoted search to handle brackets correctly
    clean_prefix = prefix.replace("[", "").replace("]", "")

    while True:
        params = {
            "query": f'"{clean_prefix}"',
            "page_size": 25
        }
        if next_cursor:
            params["next"] = next_cursor

        response = requests.get(url, params=params, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        for story in data.get("data", []):
            title_lower = story["name"].lower()
            if not title_lower.startswith(prefix.lower()):
                continue
            if story.get("workflow_state_id") not in BLOG_STATE_IDS:
                continue
            stories.append(story)

        next_url = data.get("next")
        if not next_url:
            break

        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(next_url)
        qs = parse_qs(parsed.query)
        next_cursor = qs.get("next", [None])[0]
        if not next_cursor:
            break

    return stories


def get_blog_stories():
    """
    Search Shortcut for all active stories matching blog title prefixes.
    Runs one search per prefix to avoid scanning the entire workspace.
    Returns two lists:
    - stories with a Google Doc attached
    - stories without a Google Doc yet
    """
    seen_ids = set()
    blog_stories = []
    no_doc_stories = []

    for prefix in BLOG_PREFIXES:
        stories = search_stories_by_prefix(prefix)
        print(f"  '{prefix}' → {len(stories)} stories found")

        for story in stories:
            if story["id"] in seen_ids:
                continue
            seen_ids.add(story["id"])

            google_doc_url = extract_google_doc_url(story)
            if google_doc_url:
                blog_stories.append({
                    "id": story["id"],
                    "name": story["name"],
                    "story_url": story["app_url"],
                    "google_doc_url": google_doc_url,
                    "thumbnail_status": None
                })
            else:
                no_doc_stories.append({
                    "id": story["id"],
                    "name": story["name"],
