# JobPilot AI
# Author: Md. Mahamudul Hasan
# License: GNU Affero General Public License v3
# https://www.gnu.org/licenses/agpl-3.0.en.html

"""JobPilot AI — Applied Jobs Dashboard.

A lightweight Flask web server that exposes a read/update API for the
applied-jobs history CSV and serves the job-tracking UI at ``/``.

Run with::

    python app.py

Then open http://localhost:5000 in your browser.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Any

from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS

app = Flask(__name__, template_folder="web/templates")
CORS(app)

_CSV_DIR = "all excels/"
_CSV_PATH = _CSV_DIR + "all_applied_applications_history.csv"


@app.route("/")
def home() -> str:
    """Serve the applied-jobs tracking UI.

    Returns:
        Rendered ``web/templates/index.html``.
    """
    return render_template("index.html")


@app.route("/applied-jobs", methods=["GET"])
def get_applied_jobs() -> tuple[Response, int] | Response:
    """Return a JSON list of all applied jobs from the history CSV.

    Returns:
        JSON array of job dicts, or an error payload with HTTP 404/500.
    """
    try:
        jobs: list[dict[str, str]] = []
        with open(_CSV_PATH, "r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                jobs.append(
                    {
                        "Job_ID": row.get("Job ID", ""),
                        "Title": row.get("Title", ""),
                        "Company": row.get("Company", ""),
                        "HR_Name": row.get("HR Name", ""),
                        "HR_Link": row.get("HR Link", ""),
                        "Job_Link": row.get("Job Link", ""),
                        "External_Job_link": row.get("External Job link", ""),
                        "Date_Applied": row.get("Date Applied", ""),
                        "Relevance_Score": row.get("Relevance Score", "N/A"),
                    }
                )
        return jsonify(jobs)
    except FileNotFoundError:
        return jsonify({"error": "No application history found."}), 404
    except OSError as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/applied-jobs/<job_id>", methods=["PUT"])
def update_applied_date(job_id: str) -> tuple[Response, int] | Response:
    """Mark a job as externally applied by updating its Date Applied field.

    Args:
        job_id: LinkedIn Job ID from the URL path.

    Returns:
        JSON success message (HTTP 200) or error payload with HTTP 404/500.
    """
    try:
        if not os.path.exists(_CSV_PATH):
            return jsonify({"error": f"CSV not found at {_CSV_PATH}"}), 404

        rows: list[dict[str, Any]] = []
        field_names: list[str] | None = None
        found = False

        with open(_CSV_PATH, "r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            field_names = reader.fieldnames
            for row in reader:
                if row.get("Job ID") == job_id:
                    row["Date Applied"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    found = True
                rows.append(row)

        if not found:
            return jsonify({"error": f"Job ID '{job_id}' not found."}), 404

        with open(_CSV_PATH, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=field_names)
            writer.writeheader()
            writer.writerows(rows)

        return jsonify({"message": "Date Applied updated successfully."}), 200

    except OSError as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode, host="127.0.0.1", port=5000)
