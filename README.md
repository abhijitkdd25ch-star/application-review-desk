# AICTE Application Validation Assistant — SIH prototype

A small local Flask application to demonstrate an application intake and preliminary document-checking workflow. The interface uses a restrained institutional style: navy accents, neutral surfaces, readable tables, responsive layouts and a simple application register. The styling uses local CSS and system-font fallbacks, so the dashboard does not depend on a remote UI framework or web font.

## What works in this starter version

- Redesigned responsive dashboard with application counts, recent submissions, search/filter, and clear review statuses.
- Application form with multi-file upload (PDF, PNG, JPG/JPEG).
- File size/count limits, safe stored filenames, SHA-256 hashes and exact duplicate-content detection.
- Rule-based checks for missing document type/reference, invalid dates, expired documents, future issue dates and issue/expiry order.
- Comparison against a small **fictional** issuing-authority dataset in `data/authority_records.json`.
- Evidence-linked mismatch findings, application details and a human review-note workflow.
- Local JSON persistence and an audit trail.
- Health endpoint at `/health` and basic automated tests.

## Important limitations

This is a learning/demo prototype, **not an official AICTE service**. It does not connect to AICTE systems or real issuing authorities. The sample authority records are fictional. No OCR, forgery detector, image-forensics model, regulatory-rule interpretation, user login, or production security controls are implemented in this version. A file extension and hash are not proof that a document is safe or authentic. Findings are advisory and must not be used as an automated approval/rejection decision.

Use synthetic test data only. Do not upload real personal, confidential or institutional records.

## Windows setup (PowerShell / VS Code)

1. Extract this ZIP and open the extracted folder in VS Code.
2. In VS Code choose **Terminal → New Terminal**.
3. Check Python: `py --version` (Python 3.10+ recommended).
4. Install only the core web dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

   This requirements file intentionally excludes OCR libraries such as Pillow, PyMuPDF and pytesseract, so the basic website does not try to download them. If your network has an SSL certificate issue and pip still cannot reach PyPI, use a trusted network/certificate configuration; do not disable SSL verification.

5. Start the website:

   ```powershell
   py app.py
   ```

6. Open `http://127.0.0.1:5000` in your browser.
7. Stop the server with `Ctrl+C` in the terminal.

If `py` is not recognized, try `python --version`, then use `python -m pip install -r requirements.txt` and `python app.py`.

## Demo walkthrough

1. Select **Submit application**.
2. Use the fictional institution `ABC Engineering College`.
3. Choose `Accreditation Certificate` and reference `CERT12345`.
4. Enter issue date `2024-01-10` and expiry date `2026-01-09` (expired as of late 2026, so it should flag expiry).
5. Upload a small PDF or image test file and submit.
6. Open the report, review the evidence and save a human review note.

The synthetic dataset also contains `NOC67890` for `North Demo Institute` and `FAC11111` for `ABC Engineering College`. See `data/authority_records.json` for exact values.

## Run tests

```powershell
py -m unittest discover -s tests -v
```

The unit tests for the rule engine require only the Python standard library. Flask route tests are not run automatically unless Flask is installed.

## Project map

- `app.py` — Flask routes, upload handling, JSON persistence and audit trail.
- `validator.py` — explainable rule checks and synthetic record comparison.
- `templates/` — HTML pages.
- `static/style.css` — interface styling.
- `data/authority_records.json` — fictional source records.
- `data/applications.json` — created automatically after the first submission.
- `uploads/` — local uploaded test files.
- `tests/test_validator.py` — unit tests for validation rules.

## Before any real deployment

Add authentication, role-based access, CSRF protection, private file access, malware scanning, encrypted storage, a database, backups, retention/deletion rules, reviewed AICTE rule configuration, monitoring and authorized external verification integrations. Have a qualified security review before handling real data.


## Interface notes

- The overview page includes live counts calculated from saved demo submissions.
- Search filters the visible application register by application ID, institution name or category.
- The submission, detail report, review-note and audit-history routes remain part of the same Flask app.
- The CSS is self-contained and does not require a JavaScript framework or externally hosted fonts.

## If package installation fails with an SSL certificate error

The earlier `CERTIFICATE_VERIFY_FAILED` message means pip could not validate the HTTPS certificate used by the package index; it is not a frontend-code error. Try updating certificates from your active Anaconda environment, then retry the install:

```powershell
conda install -c conda-forge certifi
python -m pip install -r requirements.txt
```

If the certificate error remains, use a trusted network or configure the correct institution/proxy CA certificate. Do not disable TLS verification or use `--trusted-host` as a workaround.
