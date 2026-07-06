import os
from dotenv import load_dotenv

load_dotenv()

# Shortcut
SHORTCUT_API_TOKEN = os.environ.get("SHORTCUT_API_TOKEN")

# Slack
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL")  # e.g. "#blog-readiness"

# Claude
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Webflow
WEBFLOW_API_TOKEN = os.environ.get("WEBFLOW_API_TOKEN")
WEBFLOW_COLLECTION_ID = os.environ.get("WEBFLOW_COLLECTION_ID")  # Blog CMS collection ID

# Google
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")  # Path to JSON file

# Shortcut config
SHORTCUT_WORKSPACE = os.environ.get("SHORTCUT_WORKSPACE")  # Your workspace slug
