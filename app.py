"""Local Flask prototype for AICTE application/document validation demos."""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, url_for, send_from_directory
from werkzeug.utils import secure_filename
from validator import validate_document

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = ROOT / "uploads"
APPLICATIONS_FILE = DATA_DIR / "applications.json"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = 25 * 1024 * 1024
CATEGORIES = ["Extension of Approval", "Change in intake / programme", "Other approval-related change"]
DOCUMENT_TYPES = ["Accreditation Certificate", "NOC", "Faculty Certificate", "Affidavit", "Infrastructure Evidence", "Other"]

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-demo-key-change-before-sharing")
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def load_apps():
    if not APPLICATIONS_FILE.exists():
        return []
    try:
        data = json.loads(APPLICATIONS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_apps(apps):
    temporary = APPLICATIONS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(apps, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(APPLICATIONS_FILE)


def allowed_file(filename):
    return bool(filename and "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS)


def add_audit(record, action, details):
    record.setdefault("audit_log", []).append({
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "action": action,
        "details": details,
    })


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@app.get("/")
def index():
    applications = sorted(load_apps(), key=lambda item: item.get("created_at", ""), reverse=True)
    stats = {
        "total": len(applications),
        "review": sum(item.get("overall_status") == "Review required" for item in applications),
        "clear": sum(item.get("overall_status") == "Initial checks passed" for item in applications),
    }
    return render_template("index.html", applications=applications, stats=stats)


@app.route("/submit", methods=["GET", "POST"])
def submit():
    if request.method == "GET":
        return render_template("submit.html", categories=CATEGORIES, document_types=DOCUMENT_TYPES)

    institution = request.form.get("institution_name", "").strip()
    category = request.form.get("application_category", CATEGORIES[0]).strip()
    if category not in CATEGORIES:
        category = CATEGORIES[0]
    document_type = request.form.get("document_type", "").strip()
    if document_type not in DOCUMENT_TYPES:
        document_type = ""
    reference = request.form.get("reference_number", "").strip()
    issue = request.form.get("issue_date", "").strip()
    expiry = request.form.get("expiry_date", "").strip()
    files = [file for file in request.files.getlist("documents") if file and file.filename]

    if not institution:
        flash("Please enter an institution name.", "error")
        return redirect(url_for("submit"))
    if len(institution) > 200:
        flash("Institution name must be 200 characters or fewer.", "error")
        return redirect(url_for("submit"))
    if not files:
        flash("Please choose at least one document to upload.", "error")
        return redirect(url_for("submit"))
    if len(files) > 10:
        flash("Please upload no more than 10 files per application.", "error")
        return redirect(url_for("submit"))

    app_id = "DEMO-" + uuid.uuid4().hex[:8].upper()
    record = {
        "id": app_id,
        "institution_name": institution,
        "application_category": category,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "documents": [],
        "audit_log": [],
        "notice": "Prototype only: synthetic records; not an official AICTE decision.",
    }
    seen_hashes = {}

    for uploaded in files:
        original = secure_filename(uploaded.filename) or "unnamed_upload"
        if not allowed_file(original):
            record["documents"].append({
                "filename": original, "document_type": document_type, "reference_number": reference,
                "issue_date": issue, "expiry_date": expiry, "verification_status": "Not processed",
                "findings": [{"level": "warning", "code": "UNSUPPORTED_FILE", "message": "Only PDF, PNG, JPG and JPEG files are accepted."}],
            })
            continue

        stored_name = f"{app_id}_{uuid.uuid4().hex[:8]}_{original}"
        destination = UPLOAD_DIR / stored_name
        uploaded.save(destination)
        size = destination.stat().st_size
        if size == 0:
            destination.unlink(missing_ok=True)
            record["documents"].append({
                "filename": original, "document_type": document_type, "reference_number": reference,
                "issue_date": issue, "expiry_date": expiry, "verification_status": "Not processed",
                "findings": [{"level": "warning", "code": "EMPTY_FILE", "message": "The uploaded file is empty. Please upload a valid file."}],
            })
            continue
        if size > MAX_FILE_BYTES:
            destination.unlink(missing_ok=True)
            record["documents"].append({
                "filename": original, "document_type": document_type, "reference_number": reference,
                "issue_date": issue, "expiry_date": expiry, "verification_status": "Not processed",
                "findings": [{"level": "warning", "code": "FILE_TOO_LARGE", "message": "Each file must be 10 MB or smaller."}],
            })
            continue

        file_hash = sha256_file(destination)
        doc = {
            "filename": original,
            "stored_name": stored_name,
            "sha256": file_hash,
            "size_bytes": size,
            "document_type": document_type,
            "reference_number": reference,
            "issue_date": issue,
            "expiry_date": expiry,
        }
        result = validate_document(doc, institution)
        doc.update(result)
        if file_hash in seen_hashes:
            doc["findings"].append({
                "level": "warning", "code": "DUPLICATE_FILE_HASH",
                "message": f"This file has identical content to another uploaded file ({seen_hashes[file_hash]}). Confirm whether it was submitted twice.",
            })
        else:
            seen_hashes[file_hash] = original
        record["documents"].append(doc)

    findings = [finding for document in record["documents"] for finding in document.get("findings", [])]
    record["total_findings"] = len(findings)
    record["overall_status"] = "Review required" if findings else "Initial checks passed"
    add_audit(record, "Application submitted", f"{len(record['documents'])} document(s) processed using local prototype rules.")
    applications = load_apps()
    applications.append(record)
    save_apps(applications)
    return redirect(url_for("detail", app_id=app_id))


@app.get("/application/<app_id>")
def detail(app_id):
    record = next((item for item in load_apps() if item.get("id") == app_id), None)
    if not record:
        flash("Application not found.", "error")
        return redirect(url_for("index"))
    return render_template("detail.html", application=record)


@app.post("/application/<app_id>/review")
def mark_reviewed(app_id):
    applications = load_apps()
    record = next((item for item in applications if item.get("id") == app_id), None)
    if not record:
        flash("Application not found.", "error")
        return redirect(url_for("index"))
    note = request.form.get("review_note", "").strip()[:2000]
    record["review_note"] = note or "Reviewed in demo; no regulatory decision recorded."
    add_audit(record, "Human review note saved", record["review_note"])
    save_apps(applications)
    flash("Demo review note saved.", "success")
    return redirect(url_for("detail", app_id=app_id))


@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    # Local demo only. A production system must enforce user/role authorization.
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=False, max_age=0)


@app.get("/health")
def health():
    return {"status": "ok", "mode": "prototype", "external_integrations": "simulated only"}


@app.errorhandler(413)
def too_large(_error):
    flash("The total upload is too large. Keep each file under 10 MB and upload no more than 10 files.", "error")
    return redirect(url_for("submit")), 303


if __name__ == "__main__":
    # Debug is disabled by default to avoid exposing the interactive debugger.
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=debug)
