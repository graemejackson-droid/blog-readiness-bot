import sys
from src.shortcut import get_blog_stories, get_thumbnail_status, get_workflow_state_name
from src.claude_classifier import classify_comments
from src.slack_reporter import send_readiness_report
from src.webflow import create_cms_draft
from src.google_docs import check_doc_readiness, get_doc_comments


def assess_story(story):
    """
    Runs all readiness checks on a single story and returns
    an enriched story dict with readiness status and reasons.
    """
    reasons = []
    ready = True
    doc_fields = {}

    # --- Google Doc checks ---
    doc_url = story["google_doc_url"]
    doc_ready, doc_reasons, doc_fields = check_doc_readiness(doc_url)
    if not doc_ready:
        ready = False
        reasons.extend(doc_reasons)

    if ready:
        doc_id = doc_url.split("/d/")[1].split("/")[0]
        comments = get_doc_comments(doc_id)
        has_blocking, classified = classify_comments(comments)
        if has_blocking:
            ready = False
            reasons.append("Blocking comments detected")

    # --- Thumbnail status ---
    workflow_state_id, thumbnail_name = get_thumbnail_status(story["id"])
    if workflow_state_id:
        thumbnail_status = get_workflow_state_name(workflow_state_id)
    else:
        thumbnail_status = "Not found"
        reasons.append("No thumbnail story linked")

    story["thumbnail_status"] = thumbnail_status
    story["ready"] = ready
    story["reasons"] = reasons
    story["doc_fields"] = doc_fields

    return story


def main():
    print("Starting weekly blog readiness scan...")

    # Step 1 — Fetch all blog stories from Shortcut
    print("Fetching stories from Shortcut...")
    all_blog_stories, no_doc_stories = get_blog_stories()
    print(f"Found {len(all_blog_stories)} blog stories with Google Docs")
    print(f"Found {len(no_doc_stories)} blog stories with no Google Doc yet")

    for s in all_blog_stories:
        print(f"  Has doc: {s['name']}")
    for s in no_doc_stories:
        print(f"  No doc: {s['name']}")

    # Step 2 — Assess each story that has a doc
    ready_stories = []
    not_ready_stories = []

    for story in all_blog_stories:
        print(f"Assessing: {story['name']}")
        assessed = assess_story(story)
        if assessed["ready"]:
            ready_stories.append(assessed)
        else:
            not_ready_stories.append(assessed)

    print(f"\nReady: {len(ready_stories)}")
    print(f"Not ready: {len(not_ready_stories)}")
    print(f"No doc yet: {len(no_doc_stories)}")

    # Step 3 — Auto-draft ready stories in Webflow (paused during QA period)
    # Uncomment when Joe and Graeme have signed off after two weeks of monitoring
    # for story in ready_stories:
    #     if story.get("doc_fields"):
    #         print(f"Creating Webflow draft for: {story['name']}")
    #         draft_url = create_cms_draft(story["name"], story["doc_fields"])
    #         if draft_url:
    #             story["webflow_draft_url"] = draft_url
    #             print(f"  Draft created: {draft_url}")
    #         else:
    #             print(f"  Draft creation failed for: {story['name']}")

    # Step 4 — Send Slack report
    print("\nSending Slack report...")
    send_readiness_report(ready_stories, not_ready_stories, no_doc_stories)

    print("\nScan complete.")


if __name__ == "__main__":
    main()
