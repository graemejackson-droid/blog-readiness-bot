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
    "page type",
    "category",
    "tags",
    "url",
    "page title",
    "meta title",
    "meta description",
    "target keywords"
]


def get_google_services():
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
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", google_doc_url)
    if match:
        return match.group(1)
    return None


def get_doc_content(doc_id):
    try:
        docs_service, _ = get_google_services()
        doc = docs_service.documents().get(documentId=doc_id).execute()
        return doc
    except Exception as e:
        print(f"Could not fetch doc {doc_id}: {e}")
        return None


def normalize_field_key(raw_key):
    """
    Normalizes a table field key by:
    - Converting to lowercase
    - Taking only the first line (strips subtext like title case instructions)
    - Removing anything in parentheses
    - Stripping extra whitespace
    """
    key = raw_key.lower()
    key = key.split("\n")[0]
    key = re.sub(r"\(.*?\)", "", key)
    key = key.strip()
    return key


def extract_table_fields(doc):
    fields = {}
    body = doc.get("body", {})

    for element in body.get("content", []):
        table = element.get("table")
        if not table:
            continue

        print(f"Found table with {len(table.get('tableRows', []))} rows")
        for row in table.get("tableRows", []):
            cells = row.get("tableCells", [])
            if len(cells) >= 2:
                raw_key = extract_text_from_cell(cells[0]).strip()
                value = extract_text_from_cell(cells[1]).strip()
                normalized_key = normalize_field_key(raw_key)
                print(f"  Table field: '{normalized_key}' = '{value[:50] if value else '(empty)'}'")
                if normalized_key:
                    fields[normalized_key] = value

        break

    if not fields:
        print("No table found at top of document")

    return fields


def extract_text_from_cell(cell):
    text = ""
    for content in cell.get("content", []):
        paragraph = content.get("paragraph", {})
        for element in paragraph.get("elements", []):
            text_run = element.get("textRun", {})
            text += text_run.get("content", "")
    return text.strip()


def has_body_content(doc):
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

    print(f"Body copy length after table: {text_length} chars")
    return text_length > 100


def get_doc_comments(doc_id):
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
        print(f"Unresolved comments found: {len(unresolved)}")
        return unresolved

    except Exception as e:
        print(f"Could not fetch comments for {doc_id}: {e}")
        return []


def map_fields_for_webflow(table_fields):
    """
    Maps Google Doc table fields to Webflow CMS field names.
    """
    return {
        "title": table_fields.get("page title", ""),
        "slug": table_fields.get("url", "").lstrip("/"),
        "meta_title": table_fields.get("meta title", ""),
        "meta_description": table_fields.get("meta description", ""),
        "tags": table_fields.get("tags", ""),
        "body": ""
    }


def extract_body_content(doc):
    """
    Extracts all text content below the first table as the blog body.
    """
    body = doc.get("body", {})
    content = body.get("content", [])
    past_first_table = False
    body_text = ""

    for element in content:
        if element.get("table"):
            past_first_table = True
            continue

        if past_first_table:
            paragraph = element.get("paragraph", {})
            line = ""
            for pe in paragraph.get("elements", []):
                line += pe.get("textRun", {}).get("content", "")
            body_text += line

    return body_text.strip()


def check_doc_readiness(google_doc_url):
    reasons = []
    doc_fields = {}

    doc_id = extract_doc_id(google_doc_url)
    if not doc_id:
        return False, ["Could not extract doc ID from URL"], doc_fields

    print(f"Checking doc: {doc_id}")
    doc = get_doc_content(doc_id)
    if not doc:
        return False, ["Could not access Google Doc — check service account sharing"], doc_fields

    # Check 1 — Table completeness
    table_fields = extract_table_fields(doc)
    missing_fields = []

    for required in REQUIRED_TABLE_FIELDS:
        matched = any(required in key for key in table_fields.keys())
        if not matched or not table_fields.get(required, "").strip():
            missing_fields.append(required)

    if missing_fields:
        reasons.append(f"Missing table fields: {', '.join(missing_fields)}")
        print(f"Missing fields: {missing_fields}")
    else:
        print("All table fields present")

    # Check 2 — Body copy
    if not has_body_content(doc):
        reasons.append("No body copy found below the metadata table")
        print("No body copy")
    else:
        print("Body copy present")

    # Build mapped fields for Webflow if ready
    if not reasons:
        body_text = extract_body_content(doc)
        doc_fields = map_fields_for_webflow(table_fields)
        doc_fields["body"] = body_text

    is_ready = len(reasons) == 0
    return is_ready, reasons, doc_fields
