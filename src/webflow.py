import requests
from config import WEBFLOW_API_TOKEN, WEBFLOW_COLLECTION_ID

BASE_URL = "https://api.webflow.com/v2"

HEADERS = {
    "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
    "Content-Type": "application/json",
    "accept": "application/json"
}


def create_cms_draft(story_name, doc_fields):
    """
    Creates a draft CMS item in Webflow from extracted Google Doc fields.
    Does NOT publish — draft only, requires human review before going live.

    doc_fields expected keys:
    - title
    - slug
    - meta_title
    - meta_description
    - body
    """
    url = f"{BASE_URL}/collections/{WEBFLOW_COLLECTION_ID}/items"

    payload = {
        "isArchived": False,
        "isDraft": True,
        "fieldData": {
            "name": doc_fields.get("title", story_name),
            "slug": doc_fields.get("slug", ""),
            "meta-title": doc_fields.get("meta_title", doc_fields.get("title", story_name)),
            "meta-description": doc_fields.get("meta_description", ""),
            "post-body": doc_fields.get("body", ""),
            "featured": False,
            "make-unlisted": True
        }
    }

    response = requests.post(url, json=payload, headers=HEADERS)

    if response.status_code in (200, 201):
        item = response.json()
        item_id = item.get("id")
        draft_url = f"https://webflow.com/dashboard/sites/collections/{WEBFLOW_COLLECTION_ID}/items/{item_id}"
        print(f"✅ Webflow draft created: {doc_fields.get('title', story_name)}")
        return draft_url
    else:
        print(f"❌ Webflow error {response.status_code}: {response.text}")
        return None


def get_collection_fields():
    """
    Utility function to inspect available fields in the Webflow CMS collection.
    """
    url = f"{BASE_URL}/collections/{WEBFLOW_COLLECTION_ID}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        collection = response.json()
        fields = collection.get("fields", [])
        print("Available Webflow CMS fields:")
        for field in fields:
            print(f"  - {field['slug']} ({field['type']})")
        return fields
    else:
        print(f"❌ Could not fetch collection: {response.status_code}")
        return []
