import requests
from urllib.parse import urlparse, parse_qs
from config import SHORTCUT_API_TOKEN

BASE_URL = "https://api.app.shortcut.com/api/v3"

HEADERS = {
    "Content-Type": "application/json",
    "Shortcut-Token": SHORTCUT_API_TOKEN
}

BLOG_STATE_IDS = (
    500000015,
    500006100,
    500312330,
    500312332,
    500315599,
    500317381,
    500317382,
    500330893,
    500330894,
    500331212,
    500331214,
    500331414,
    500334421,
    500334423,
    500371811,
    500371812,
    500372008,
    500372009,
    500372699,
    500372700,
    500372701,
    500373311,
    500373312,
    500389406,
    500389407,
    500390431,
    500390428,
    500391935,
    500391936,
    500406321,
    500406323,
)


def search_blog_stories():
    """
    Search Shortcut for all stories with 'blog' anywhere in the title.
    Filters by active workflow state IDs in Python after fetching.
    Paginates through all results.
    """
    url = f"{BASE_URL}/search/stories"
    stories = []
    next_cursor = None

    while True:
        params = {
            "query": '"blog"',
            "page_size": 25
        }
        if next_cursor:
            params["next"] = next_cursor

        try:
            response = requests.get(url, params=params, headers=HEADERS)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"  ⚠️ Search error: {e} — stopping pagination")
            break

        data = response.json()

        for story in data.get("data", []):
            if "blog" not in story["name"].lower():
                continue
            if story.get("workflow_state_id") not in BLOG_STATE_IDS:
                continue
            stories.append(story)

        next_url = data.get("next")
        if not next_url:
            break

        parsed = urlparse(next_url)
        qs = parse_qs(parsed.query)
        next_cursor = qs.get("next", [None])[0]
        if not next_cursor:
            break

    print(f"  'blog' → {len(stories)} stories found")
    return stories


def get_blog_stories():
    """
    Fetches all active blog stories and splits into two lists:
    - stories with a Google Doc attached
    - stories without a Google Doc yet
    """
    seen_ids = set()
    blog_stories = []
    no_doc_stories = []

    stories = search_blog_stories()

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
    Look for a Google Doc URL in:
    1. External links
    2. Description
    3. Comments (most common location for blog stories)
    """
    # Check external links first
    for link in story.get("external_links", []):
        if "docs.google.com" in link:
            return link

    # Check description
    description = story.get("description", "")
    for word in description.split():
        if "docs.google.com" in word:
            return word.strip()

    # Check comments — scan all comment text for Google Doc URLs
    for comment in story.get("comments", []):
        text = comment.get("text", "")
        for word in text.split():
            clean_word = word.strip("*[]()\"'")
            if "docs.google.com" in clean_word:
                return clean_word

    return None


def get_thumbnail_status(story_id):
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
    url = f"{BASE_URL}/stories/{story_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return None


def get_workflow_state_name(workflow_state_id):
    url = f"{BASE_URL}/workflows"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    for workflow in response.json():
        for state in workflow.get("states", []):
            if state["id"] == workflow_state_id:
                return state["name"]

    return "Unknown"


def debug_workflow_states():
    url = f"{BASE_URL}/workflows"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    for workflow in response.json():
        print(f"Workflow: {workflow['name']}")
        for state in workflow.get("states", []):
            print(f"  - [{state['type']}] {state['name']} (id: {state['id']})")
