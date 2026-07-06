import sys
from src.shortcut import get_blog_stories, get_thumbnail_status, get_workflow_state_name, debug_workflow_states
from src.claude_classifier import classify_comments
from src.slack_reporter import send_readiness_report


def assess_story(story):
    """
    Runs all readiness checks on a single story and returns
    an enriched story dict with readiness status and reasons.
    """
    reasons = []
    ready = True

    # --- Google Doc checks (enabled once IT provides service account JSON) ---
    # doc_url = story["google_doc_url"]
    # doc_ready, doc_reasons = check_doc_readiness(doc_url)
    # if not doc_ready:
    #     ready = False
    #     reasons.extend(doc_reasons)
    #
    # comments = get_doc_comments(doc_url)
    # has_blocking, classified = classify_comments(comments)
    # if has_blocking:
    #     ready = False
    #     reasons.append("Blocking comments detected")

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

    return story


def main():
    print("🔍 Starting weekly blog readiness scan...")

    # Temporary: print all workflow state names to verify exact naming
    print("\n--- Workflow States in your Shortcut workspace ---")
    debug_workflow_states()
    print("---------------------------------------------------\n")

    # Step 1 — Fetch all blog-prefixed stories from Shortcut
    print("Fetching stories from Shortcut...")
    all_blog_stories, no_doc_stories = get_blog_stories()
    print(f"Found {len(all_blog_stories)} blog stories with Google Docs")
    print(f"Found {len(no_doc_stories)} blog stories with no Google Doc yet")

    for s in all_blog_stories:
        print(f"  ✅ Has doc: {s['name']}")
    for s in no_doc_stories:
        print(f"  📄 No doc: {s['name']}")

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

    print(f"\n✅ Ready: {len(ready_stories)}")
    print(f"⚠️  Not ready: {len(not_ready_stories)}")
    print(f"📄 No doc yet: {len(no_doc_stories)}")

    # Step 3 — Send Slack report
    print("\nSending Slack report...")
    send_readiness_report(ready_stories, not_ready_stories, no_doc_stories)

    print("\n🎉 Scan complete.")


if __name__ == "__main__":
    main()
