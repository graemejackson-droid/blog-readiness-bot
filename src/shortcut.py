import requests
from config import SHORTCUT_API_TOKEN

BASE_URL = "https://api.app.shortcut.com/api/v3"

HEADERS = {
    "Content-Type": "application/json",
    "Shortcut-Token": SHORTCUT_API_TOKEN
}

def get_blog_stories():
    """
    Search Shortcut for all in-progress or unstarted stories
    that have a Google Doc link attached — our blog relevance filter.
    """
    url = f"{BASE_URL}/search/stories"
    payload = {
        "query": "!is:done !is:archived",
        "page_size": 25
    }

    response = requests.get(url, params=payload, headers=HEADERS)
    response.raise_for_status()
    stories = response.json().get("data", [])

    blog_stories = []
    for story in stories:
        google_doc_url = extract_google_doc_url(story)
        if google_doc_url:
            blog_stories.append({
                "id": story["id"],
                "name": story["name"],
                "story_url": story["app_url"],
                "google_doc_url": google_doc_url,
                "thumbnail_status": None
            })

    return blog_stories


def extract_google_doc_url(story):
    """
    Look for a Google Doc URL in the story's external links or description.
    """
    # Check external links first
    for link in story.get("external_links", []):
        if "docs.google.com" in link:
            return link

    # Fall back to scanning description for a Google Doc URL
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
