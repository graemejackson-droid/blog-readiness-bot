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
        print(f"  ❌ Could not fetch doc {doc_id}: {e}")
        return None


def extract_table_fields(doc):
    fields = {}
    body = doc.get("body", {})

    for element in body.get("content", []):
        table = element.get("table")
        if not table:
            continue

        print(f"  📋 Found table with {len(table.get('tableRows', []))} rows")
        for row in table.get("tableRows", []):
            cells = row.get("tableCells", [])
            if len(cells) >= 2:
                key = extract_text_from_cell(cells[0]).strip().lower()
                value = extract_text_from_cell(cells[1]).strip()
                print(f"    Table field: '{key}' = '{value[:50] if value else '(empty)'}'")
                if key:
                    fields[key] = value

        break

    if not fields:
        print("  ⚠️ No table found at top of document")

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

    print(f"  📝 Body copy length after table: {text_length} chars")
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
        print(f"  💬 Unresolved comments found: {len(unresolved)}")
        return unresolved

    except Exception as e:
        print(f"  ❌ Could not fetch comments for {doc_id}: {e}")
        return []


def check_doc_readiness(google_doc_url):
    reasons = []
    doc_fields = {}

    doc_id = extract_doc_id(google_doc_url)
    if not doc_id:
        return False, ["Could not extract doc ID from URL"], doc_fields

    print(f"  🔍 Checking doc: {doc_id}")
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
        print(f"  ❌ Missing fields: {missing_fields}")
    else:
        print(f"  ✅ All table fields present")

    # Check 2 — Body copy
    if not has_body_content(doc):
        reasons.append("No body copy found below the metadata table")
        print(f"  ❌ No body copy")
    else:
        print(f"  ✅ Body copy present")

    is_ready = len(reasons) == 0
    return is_ready, reasons, doc_fields
