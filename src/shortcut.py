import requests
from urllib.parse import urlparse, parse_qs
from config import SHORTCUT_API_TOKEN

BASE_URL = "https://api.app.shortcut.com/api/v3"

HEADERS = {
    "Content-Type": "application/json",
    "Shortcut-Token": SHORTCUT_API_TOKEN
}

# All active workflow states excluding Icebox and Completed across all workflows
BLOG_STATE_IDS = (
    # Default
    500015824,   # Triage
    500000014,   # Backlog
    500281758,   # On Deck
    500000011,   # Committed
    500000015,   # In Progress
    500006100,   # Needs Verification
    # Experiment
    500312325,   # Triage
    500384098,   # Engineering Backlog
    500399336,   # Committed
    500312330,   # Development
    500354393,   # Design QA
    500312329,   # Code Review
    500312332,   # Needs Verification
    500354394,   # CX In Progress
    # Simplified
    500318968,   # Triage
    500315598,   # Ready for Development
    500315599,   # In Process
    # Fanatics
    500317376,   # Triage
    500317387,   # Discovery
    500317378,   # Backlog
    500317379,   # On Deck
    500317380,   # Committed
    500317381,   # In Progress
    500317831,   # Code Review
    500317382,   # Needs Verification
    500319576,   # Design QA
    # Basketball
    500330888,   # Triage
    500330890,   # Backlog
    500330891,   # On Deck
    500330892,   # Committed
    500330893,   # In Progress
    500330897,   # Code Review
    500330894,   # QA Testing
    500330898,   # Design QA
    # A-Team
    500331207,   # Triage
    500331209,   # Backlog
    500331210,   # On Deck
    500331211,   # Committed
    500331212,   # In Progress
    500331213,   # Code Review
    500331214,   # Needs Verification
    500331215,   # Design QA
    # App Platform
    500331409,   # Triage
    500331411,   # Backlog
    500331413,   # Committed
    500331414,   # In Progress
    500331418,   # Code Review
    500331415,   # Merged
    # Insights Hub
    500334419,   # Triage
    500334420,   # Ready for Development
    500334421,   # In Process
    500334423,   # Ready For Review
    500371811,   # In Progress
    500371813,   # Blocked
    500371812,   # Needs Review
    # Activators
    500372006,   # Triage
    500372017,   # On Deck
    500372018,   # Committed
    500372008,   # In Progress
    500372019,   # Code Review
    500372009,   # Needs Verification
    500372010,   # Release
    500372020,   # Monitor
    # User Acquisition
    500372697,   # Triage
    500377890,   # Backlog
    500372698,   # Ready for Development
    500372699,   # In Development
    500372700,   # Ready for Review
    500381392,   # DQA
    500372701,   # Needs Verification
    # Stats & Insights
    500373306,   # Triage
    500373308,   # Backlog
    500373309,   # On Deck
    500373310,   # Committed
    500373311,   # In Progress
    500373320,   # Code Review
    500373312,   # Needs Verification
    500373319,   # Design QA
    # BD
    500376492,   # Triage
    500376606,   # Planning
    500376493,   # In Progress
    500376500,   # External Review
    500376608,   # Approved
    # InfoSec
    500381501,   # Ready for Work
    500381502,   # In Process
    500381505,   # Blocked
    # CV Platform Team
    500389402,   # Triage
    500389404,   # On Deck
    500389405,   # Committed
    500389406,   # In Progress
    500389407,   # Needs Verification
    # Snowplow
    500390425,   # In Draft
    500390426,   # Ready for Analytics
    500390431,   # Analytics In Progress
    500390427,   # Ready for Engineering
    500390428,   # Engineering In Progress
    500390429,   # Ready for Production
    500390437,   # In Production
    # Analytics Team
    500391934,   # Ready for Development
    500391935,   # In Development
    500391936,   # Ready for Review
    500391937,   # Ready for Deploy
    # AI Enablement
    500406319,   # On Deck
    500406320,   # Committed
    500406321,   # In Progress
    500406322,   # Code Review
    500406323,   # Needs Verification
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
            print(f"Search error: {e} — stopping pagination")
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

    print(f"  'blog' -> {len(stories)} stories found")
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
    for link in story.get("external_links", []):
        if "docs.google.com" in link:
            return link

    description = story.get("description", "")
    for word in description.split():
        if "docs.google.com" in word:
            return word.strip()

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
