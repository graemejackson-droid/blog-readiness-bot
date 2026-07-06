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

BLOG_STATE_IDS = (
    500000015,   # Default workflow: In Progress
    500006100,   # Default workflow: Needs Verification
    500389406,   # CV Platform Team: In Progress
    500389407,   # CV Platform Team: Needs Verification
    500406321,   # AI Enablement: In Progress
    500406323,   # AI Enablement: Needs Verification
)


def search_stories_by_prefix(prefix):
    """
    Search Shortcut for non-archived stories whose title contains the prefix.
    Filters by workflow state ID after fetching.
    Paginates through all results.
    """
    url = f"{BASE_URL}/search/stories"
    stories = []
    next_cursor = None

    # Strip brackets for the search query since they're special characters
    clean_prefix = prefix.replace("[", "").replace("]", "")

    while True:
        params = {
            "query": f'{clean_prefix} !is:archived',
            "page_size": 25
        }
        if next_cursor:
            params["next"] = next_cursor

        response = requests.get(url, params=params, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        for story in data.get("data", []):
            # Filter by title prefix (case insensitive)
            title_lower = story["name"].lower()
            if not title_lower.startswith(prefix.lower()):
                continue
            # Filter by workflow state
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
    Search Shortcut for all stories in active states matching blog title prefixes.
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
                    "story_url": story["app_url"],
                    "thumbnail_status": None
                })

    return blog_stories, no_doc_stories


def extract_google_doc_url(story):
    """
    Look for a Google Doc URL in the story's external links or description.
    """
    for link in story.get("external_links", []):
        if "docs.google.com" in link:
            return link

    description = story.get("description", "")
    for word in description.split():
        if "docs.google.com" in word:
            return word.strip()

    return None


def get_thumbnail_status(story_id):
    """
    Find the related thumbnail story and return its current workflow state.
    """
    url = f"{BASE_URL}/stories/{story_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    story = response.json()

    for related in story.get("story_links", []):
        related_id = related.get("object_id")
        if related_id:
            related_story = get_story_by_id(related_id)
            if related_story and "thumbnail" in related_story.get("name", "").lower():
                return related_story.get("workflow_state_id"), related_story.get("name")

    return None, None


def get_story_by_id(story_id):
    """
    Fetch a single story by ID.
    """
    url = f"{BASE_URL}/stories/{story_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return None


def get_workflow_state_name(workflow_state_id):
    """
    Resolve a workflow state ID to its human-readable name.
    """
    url = f"{BASE_URL}/workflows"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    for workflow in response.json():
        for state in workflow.get("states", []):
            if state["id"] == workflow_state_id:
                return state["name"]

    return "Unknown"


def debug_workflow_states():
    """
    Prints all workflow names and their states — used to verify exact state names.
    """
    url = f"{BASE_URL}/workflows"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    for workflow in response.json():
        print(f"Workflow: {workflow['name']}")
        for state in workflow.get("states", []):
            print(f"  - [{state['type']}] {state['name']} (id: {state['id']})")
