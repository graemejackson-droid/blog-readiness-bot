from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import SLACK_BOT_TOKEN, SLACK_CHANNEL
from datetime import date

client = WebClient(token=SLACK_BOT_TOKEN)

def send_readiness_report(ready_stories, not_ready_stories):
    """
    Formats and sends the weekly blog readiness report to Slack.
    """
    today = date.today().strftime("%B %d, %Y")
    blocks = []

    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"📋 Weekly Blog CMS Readiness — {today}"
        }
    })

    blocks.append({"type": "divider"})

    # Ready stories
    if ready_stories:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*✅ Ready for CMS Transfer ({len(ready_stories)})*"
            }
        })
        for story in ready_stories:
            thumbnail = story.get("thumbnail_status") or "Not found"
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• <{story['story_url']}|{story['name']}>\n  _Thumbnail: {thumbnail}_"
                }
            })
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*✅ Ready for CMS Transfer (0)*\n_No posts ready this week._"
            }
        })

    blocks.append({"type": "divider"})

    # Not ready stories
    if not_ready_stories:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*⚠️ Not Yet Ready ({len(not_ready_stories)})*"
            }
        })
        for story in not_ready_stories:
            reasons = ", ".join(story.get("reasons", ["Unknown"]))
            thumbnail = story.get("thumbnail_status") or "Not found"
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• <{story['story_url']}|{story['name']}>\n  _Blocking: {reasons}_\n  _Thumbnail: {thumbnail}_"
                }
            })
    else:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*⚠️ Not Yet Ready (0)*\n_All posts are ready this week!_ 🎉"
            }
        })

    # Footer
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "Powered by Blog Readiness Bot · <https://github.com/gamechangerodyssey/blog-readiness-bot|View on GitHub>"
            }
        ]
    })

    try:
        client.chat_postMessage(
            channel=SLACK_CHANNEL,
            blocks=blocks,
            text=f"Weekly Blog CMS Readiness Report — {today}"
        )
        print("✅ Slack report sent successfully")
    except SlackApiError as e:
        print(f"❌ Slack error: {e.response['error']}")
