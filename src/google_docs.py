import os
import json
import re
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

REQUIRED_TABLE_FIELDS = [
    "title",
    "author",
    "publish date",
    "meta description",
    "slug",
    "tags"
]


def get_google_services():
    """
    Authenticates using the service account JSON stored in the
    GOOGLE_SERVICE_ACCOUNT_JSON environment variable.
    Returns (docs_service, drive_service) tuple.
    """
    service_account_info = json.loads(
        os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    )

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES
    )

    docs_service = build("docs", "v1", credentials=credentials)
    drive_service = build("drive", "v3", credentials=credentials)

    return docs_service, drive_service


def extract_doc_id(google_doc_url):
    """
    Extracts the document ID from a Google Docs URL.
    Handles formats like:
    - https://docs.google.com/document/d/DOC_ID/edit
    - https://docs.google.com/document/d/DOC_ID/edit?usp=sharing
    """
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", google_doc_url)
    if match:
        return match.group(1)
    return None


def get_doc_content(doc_id):
    """
    Fetches the full document content from Google Docs API.
    Returns the document object or None on failure.
    """
    try:
        docs_service, _ = get_google_services()
        doc = docs_service.documents().get(documentId=doc_id).execute()
        return doc
    except Exception as e:
        print(f"  ❌ Could not fetch doc {doc_id}: {e}")
        return None


def extract_table_fields(doc):
    """
    Parses the metadata table at the top of the document.
    Returns a dict of field_name -> value.
    Assumes the table is the first table in the document.
    """
    fields = {}
    body = doc.get("body", {})

    for element in body.get("content", []):
        table = element.get("table")
        if not table:
            continue

        # Found the first table — parse it
        for row in table.get("tableRows", []):
            cells = row.get("tableCells", [])
            if len(cells) >= 2:
                # First cell is the field name, second is the value
                key = extract_text_from_cell(cells[0]).strip().lower()
                value = extract_text_from_cell(cells[1]).strip()
                if key:
                    fields[key] = value

        break  # Only parse the first table

    return fields


def extract_text_from_cell(cell):
    """
    Extracts plain text from a table cell.
    """
    text = ""
    for content in cell.get("content", []):
        paragraph = content.get("paragraph", {})
        for element in paragraph.get("elements", []):
            text_run = element.get("textRun", {})
            text += text_run.get("content", "")
    return text.strip()


def has_body_content(doc):
    """
    Checks whether there is substantive text content below the first table.
    Returns True if body copy is present.
    """
    body = doc.get("body", {})
    content = body.get("content", [])
    past_first_table = False
    text_length = 0

    for element in content:
        if element.get("table"):
            past_first_table = True
            continue

        if past_first_table:
            paragraph = element.get("paragraph", {})
            for pe in paragraph.get("elements", []):
                text = pe.get("textRun", {}).get("content", "").strip()
                text_length += len(text)

    return text_length > 100  # At least 100 chars of body copy


def get_doc_comments(doc_id):
    """
    Fetches all unresolved comments from the Google Doc via Drive API.
    Returns a list of comment text strings.
    """
    try:
        _, drive_service = get_google_services()
        result = drive_service.comments().list(
            fileId=doc_id,
            fields="comments(content,resolved)",
            includeDeleted=False
        ).execute()

        unresolved = [
            c["content"]
            for c in result.get("comments", [])
            if not c.get("resolved", False)
        ]
        return unresolved

    except Exception as e:
        print(f"  ❌ Could not fetch comments for {doc_id}: {e}")
        return []


def check_doc_readiness(google_doc_url):
    """
    Main readiness check function. Runs all three checks:
    1. Metadata table is complete
    2. Body copy is present
    3. No blocking comments (handled separately via claude_classifier)

    Returns (is_ready, list_of_failure_reasons, doc_fields_dict)
    """
    reasons = []
    doc_fields = {}

    doc_id = extract_doc_id(google_doc_url)
    if not doc_id:
        return False, ["Could not extract doc ID from URL"], doc_fields

    doc = get_doc_content(doc_id)
    if not doc:
        return False, ["Could not access Google Doc — check service account sharing"], doc_fields

    # Check 1 — Table completeness
    table_fields = extract_table_fields(doc)
    doc_fields = table_fields
    missing_fields = []

    for required in REQUIRED_TABLE_FIELDS:
        matched = any(required in key for key in table_fields.keys())
        if not matched or not table_fields.get(required, "").strip():
            missing_fields.append(required)

    if missing_fields:
        reasons.append(f"Missing table fields: {', '.join(missing_fields)}")

    # Check 2 — Body copy
    if not has_body_content(doc):
        reasons.append("No body copy found below the metadata table")

    is_ready = len(reasons) == 0
    return is_ready, reasons, doc_fields
