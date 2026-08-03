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
        print(f"  ❌ Could not fetch doc {doc_id}: {e}")
        return None


def normalize_field_key(raw_key):
    """
    Normalizes a table field key by:
    - Converting to lowercase
    - Stripping newlines
    - Removing parenthetical notes e.g. "(title case, 60 character max)"
    - Stripping extra whitespace
    """
    key = raw_key.lower()
    key = key.split("\n")[0]  # Take only the first line
    key = re.sub(r"\(.*?\)", "", key)  # Remove anything in parentheses
    key = key.strip()
    return key


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
                raw_key = extract_text_from_cell(cells[0]).strip()
                value = extract_text_from_cell(cells[1]).strip()
                normalized_key = normalize_field_key(raw_key)
                print(f"    Table field: '{normalized_key}' = '{value[:50] if value else '(empty)'}'")
                if normalized_key:
                    fields[normalized_key] = value

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

    print(f"  Body copy length after table: {text_length} chars")
