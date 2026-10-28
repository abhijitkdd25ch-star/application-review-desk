"""Transparent, rule-based checks for the AICTE demo prototype.

This module uses synthetic records only. It is not an official verification service.
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUTHORITY_FILE = ROOT / "data" / "authority_records.json"


def load_authority_records():
    try:
        with AUTHORITY_FILE.open("r", encoding="utf-8") as handle:
            records = json.load(handle)
        return records if isinstance(records, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def validate_document(doc, institution_name):
    """Return transparent advisory findings for a single uploaded document."""
    findings = []
    today = date.today()

    if not doc.get("filename"):
        findings.append({"level": "error", "code": "MISSING_FILE", "message": "No file was uploaded."})
    if not doc.get("document_type"):
        findings.append({"level": "warning", "code": "MISSING_TYPE", "message": "Document type was not selected."})
    if not doc.get("reference_number"):
        findings.append({"level": "warning", "code": "MISSING_REFERENCE", "message": "Reference number is missing; source verification cannot be attempted."})

    issue_raw = (doc.get("issue_date") or "").strip()
    expiry_raw = (doc.get("expiry_date") or "").strip()
    issue = _parse_date(issue_raw)
    expiry = _parse_date(expiry_raw)

    if issue_raw and issue is None:
        findings.append({"level": "warning", "code": "INVALID_ISSUE_DATE", "message": "Issue date is not a valid YYYY-MM-DD date."})
    if expiry_raw and expiry is None:
        findings.append({"level": "warning", "code": "INVALID_EXPIRY_DATE", "message": "Expiry date is not a valid YYYY-MM-DD date."})
    if expiry and expiry < today:
        findings.append({"level": "warning", "code": "EXPIRED", "message": f"Expiry date {expiry.isoformat()} is before today's date ({today.isoformat()})."})
    if issue and expiry and issue > expiry:
        findings.append({"level": "warning", "code": "DATE_ORDER", "message": "Issue date is later than expiry date."})
    if issue and issue > today:
        findings.append({"level": "warning", "code": "FUTURE_ISSUE_DATE", "message": "Issue date is in the future; confirm the date and document context."})

    records = load_authority_records()
    reference = (doc.get("reference_number") or "").strip().upper()
    match = next((r for r in records if str(r.get("reference_number", "")).strip().upper() == reference), None)
    if reference and match:
        comparisons = []
        if doc.get("document_type") and str(match.get("document_type", "")).casefold() != str(doc["document_type"]).casefold():
            comparisons.append("document type differs from synthetic source record")
        if institution_name and str(match.get("institution_name", "")).casefold() != str(institution_name).casefold():
            comparisons.append("institution name differs from synthetic source record")
        if issue_raw and match.get("issue_date") and issue_raw != match["issue_date"]:
            comparisons.append("issue date differs from synthetic source record")
        if expiry_raw and match.get("expiry_date") and expiry_raw != match["expiry_date"]:
            comparisons.append("expiry date differs from synthetic source record")
        if comparisons:
            findings.append({
                "level": "warning", "code": "SOURCE_MISMATCH",
                "message": "Possible mismatch: " + "; ".join(comparisons) + ".",
                "evidence": {"submitted_reference": reference, "synthetic_record": match}
            })
            verification = "Mismatch detected"
        else:
            verification = "Matched synthetic test record"
    elif reference:
        verification = "Manual review required — no matching synthetic test record"
        findings.append({"level": "info", "code": "NO_TEST_RECORD", "message": "No matching record exists in the prototype's synthetic dataset. This does not mean the document is fake."})
    else:
        verification = "Not checked — reference number missing"

    return {"verification_status": verification, "findings": findings}
