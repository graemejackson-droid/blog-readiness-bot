import sys
from src.shortcut import get_blog_stories, get_thumbnail_status, get_workflow_state_name
from src.claude_classifier import classify_comments
from src.slack_reporter import send_readiness_report

# Google Docs import — commented out until service account JSON is received from IT
# from src.google_docs import check_doc_readiness, get_doc_comments

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
    story["reasons"] = reasons if reasons else []

    return story


def main():
    print("🔍 Starting weekly blog readiness scan...")

    # Step 1 — Fetch blog stories from Shortcut
    print("Fetching stories from Shortcut...")
    stories = get_blog_stories()
    print(f"Found {len(stories)} blog-relevant stories")

    if not stories:
        print("No blog stories found. Exiting.")
        sys.exit(0)

    # Step 2 — Assess each story
    ready_stories = []
    not_ready_stories = []

    for story in stories:
        print(f"Assessing: {story['name']}")
        assessed = assess_story(story)

        if assessed["ready"]:
            ready_stories.append(assessed)
        else:
            not_ready_stories.append(assessed)

    print(f"\n✅ Ready: {len(ready_stories)}")
    print(f"⚠️  Not ready: {len(not_ready_stories)}")

    # Step 3 — Send Slack report
    print("\nSending Slack report...")
    send_readiness_report(ready_stories, not_ready_stories)

    print("\n🎉 Scan complete.")


if __name__ == "__main__":
    main()
