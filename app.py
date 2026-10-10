from flask import Flask, render_template, jsonify, request
import requests
import sqlite3
from pathlib import Path
app = Flask(__name__)
DATABASE = Path(__file__).with_name("resqmap.db")


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection



def init_db():
    with get_db_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                location TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                disaster_type TEXT,
                description TEXT,
                assistance TEXT,
                damage TEXT DEFAULT 'Unassessed',
                damage_points INTEGER DEFAULT 50,
                people_affected INTEGER DEFAULT 0,
                life_safety INTEGER DEFAULT 50,
                accessibility INTEGER DEFAULT 50,
                immediate_threat INTEGER DEFAULT 0,
                safety_status TEXT,
                status TEXT DEFAULT 'Pending inspection'
            )
        """)

        # Add the original demo incidents only when the table is empty.
        count = connection.execute(
            "SELECT COUNT(*) FROM incidents"
        ).fetchone()[0]

        if count == 0:
            for item in INCIDENTS:
                connection.execute("""
                    INSERT INTO incidents (
                        id, location, latitude, longitude, damage,
                        damage_points, people_affected, life_safety,
                        accessibility, immediate_threat, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item["id"],
                    item["location"],
                    item["latitude"],
                    item["longitude"],
                    item["damage"],
                    item["damage_points"],
                    item["people_affected"],
                    item["life_safety"],
                    item["accessibility"],
                    int(item["immediate_threat"]),
                    item["status"],
                ))
INCIDENTS = [
    {
        "id": "RQM-001",
        "location": "Sector A-12",
        "latitude": 16.5062,
        "longitude": 80.6480,
        "damage": "High",
        "damage_points": 90,
        "people_affected": 12,
        "life_safety": 100,
        "accessibility": 70,
        "immediate_threat": True,
        "status": "Pending inspection",
    },
    {
        "id": "RQM-002",
        "location": "Sector B-04",
        "latitude": 16.5150,
        "longitude": 80.6350,
        "damage": "Moderate",
        "damage_points": 55,
        "people_affected": 20,
        "life_safety": 50,
        "accessibility": 40,
        "immediate_threat": False,
        "status": "Pending inspection",
    },
    {
        "id": "RQM-003",
        "location": "Sector C-09",
        "latitude": 16.4950,
        "longitude": 80.6600,
        "damage": "Low",
        "damage_points": 20,
        "people_affected": 3,
        "life_safety": 20,
        "accessibility": 15,
        "immediate_threat": False,
        "status": "Field verified",
    },
    {
        "id": "RQM-004",
        "location": "Sector D-02",
        "latitude": 16.5220,
        "longitude": 80.6700,
        "damage": "High",
        "damage_points": 85,
        "people_affected": 8,
        "life_safety": 70,
        "accessibility": 80,
        "immediate_threat": False,
        "status": "Pending inspection",
    },
]


def calculate_priority(incident):
    """Calculate an explainable, illustrative priority score."""

    # Normalize the number of affected people to a 0–100 scale.
    people_score = min(incident["people_affected"] / 50 * 100, 100)

    score = round(
        incident["life_safety"] * 0.35
        + incident["damage_points"] * 0.25
        + people_score * 0.20
        + incident["accessibility"] * 0.20
    )

    reasons = []

    if incident["life_safety"] >= 70:
        reasons.append("High life-safety concern")

    if incident["damage_points"] >= 70:
        reasons.append("High reported damage estimate")

    if incident["people_affected"] >= 10:
        reasons.append("Many people affected")

    if incident["accessibility"] >= 70:
        reasons.append("Difficult rescue access")

    if not reasons:
        reasons.append("Further assessment may be required")

    # A reported immediate threat is flagged independently
    # of the calculated score.
    if incident["immediate_threat"]:
        priority = "IMMEDIATE"
    elif score >= 70:
        priority = "HIGH"
    elif score >= 40:
        priority = "MODERATE"
    else:
        priority = "LOW"

    result = incident.copy()
    result["score"] = score
    result["priority"] = priority
    result["reason"] = "; ".join(reasons)
    result["confidence"] = "Rule-based demo; not AI-verified"

    return result


@app.route("/")
def dashboard():
    return render_template("index.html")
@app.route("/report")
def report_page():
    return render_template("report.html")

def recommend_assistance(disaster_type, people_affected=0):
    disaster = (disaster_type or "").strip().lower()
    people = int(people_affected or 0)

    recommendations = {
        "fire": [
            "Fire and rescue team",
            "Emergency medical support",
            "Evacuation and temporary shelter"
        ],
        "flood": [
            "Rescue boats and life jackets",
            "Safe drinking water and food",
            "Medical support and temporary shelter"
        ],
        "earthquake": [
            "Urban search and rescue team",
            "First aid and medical supplies",
            "Temporary shelter and clean water"
        ],
        "cyclone": [
            "Evacuation and safe shelter",
            "Food and drinking water",
            "Medical supplies and emergency power"
        ],
        "landslide": [
            "Search and rescue team",
            "Medical support",
            "Road access assessment and temporary shelter"
        ],
        "other": [
            "Emergency assessment team",
            "First aid and medical support",
            "Food, water and safe shelter"
        ]
    }

    result = recommendations.get(
        disaster,
        recommendations["other"]
    ).copy()
    if people >= 50:
        result.append("Additional relief teams for a large affected population")

    if people >= 100:
        result.append("Coordinate additional supplies and evacuation capacity")
    return result
@app.route("/api/incidents", methods=["GET"])
def get_incidents():
    with get_db_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM incidents"
        ).fetchall()

    incidents = []

    for row in rows:
        incident = dict(row)

        incident["immediate_threat"] = bool(
            incident.get("immediate_threat")
        )

        priority_data = calculate_priority(incident)
        incident.update(priority_data)
        incident["recommended_assistance"] = recommend_assistance(
        incident.get("disaster_type"),
        incident.get("people_affected", 0)
)
        incidents.append(incident)

    incidents.sort(
        key=lambda item: (
            item.get("priority") == "IMMEDIATE",
            item.get("score", 0)
        ),
        reverse=True
    )
    return jsonify(incidents)
@app.route("/api/incidents", methods=["POST"])
def create_incident():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON report."}), 400
    # Validate required fields.
    required_fields = [
        "disaster_type",
        "location",
        "people_affected",
        "life_safety",
        "assistance",
        "description",
    ]
    for field in required_fields:
        if field not in data or data[field] is None or str(data[field]).strip() == "":
            return jsonify({"error": f"Missing required field: {field}"}), 400

    location = str(data["location"]).strip()
    description = str(data["description"]).strip()
    disaster_type = str(data["disaster_type"]).strip()
    assistance = str(data["assistance"]).strip()

    if not location or not description:
        return jsonify({"error": "Location and description cannot be empty."}), 400

    # Validate the number of people affected.
    try:
        people_affected = int(data["people_affected"])
        if people_affected < 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "People affected must be a non-negative integer."}), 400

    # Accept either the text value from the form or a boolean.
    raw_safety = data["life_safety"]

    if isinstance(raw_safety, bool):
        safety_status = "yes" if raw_safety else "no"
    else:
        safety_status = str(raw_safety).strip().lower()

    if safety_status not in ("yes", "no", "unknown"):
        return jsonify({"error": "Invalid immediate-danger selection."}), 400

    # Validate optional GPS coordinates.
    try:
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        latitude = None if latitude in (None, "") else float(latitude)
        longitude = None if longitude in (None, "") else float(longitude)

        if (latitude is None) != (longitude is None):
            return jsonify({
                "error": "Enter both latitude and longitude, or leave both blank."
            }), 400

        if latitude is not None:
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                return jsonify({"error": "GPS coordinates are out of range."}), 400

    except (ValueError, TypeError):
        return jsonify({"error": "GPS coordinates must be valid numbers."}), 400

    # These are provisional rule-based estimates, not verified damage findings.
    if safety_status == "yes":
        life_safety_score = 100
    elif safety_status == "unknown":
        life_safety_score = 50
    else:
        life_safety_score = 0

    # Create a unique ID using the existing sample-record count.
    incident_id = next_incident_id()
    incident = {
        "id": incident_id,
        "location": location,
        "latitude": latitude,
        "longitude": longitude,
        "disaster_type": disaster_type,
        "description": description,
        "assistance": assistance,
        "damage": "Unassessed",
        "damage_points": 50,
        "people_affected": people_affected,
        "life_safety": life_safety_score,
        "accessibility": 50,
        "immediate_threat": safety_status == "yes",
        "safety_status": safety_status,
        "status": "Pending inspection",
    }
    with get_db_connection() as connection:
     connection.execute("""
        INSERT INTO incidents (
            id, location, latitude, longitude, disaster_type,
            description, assistance, damage, damage_points,
            people_affected, life_safety, accessibility,
            immediate_threat, safety_status, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        incident["id"],
        incident["location"],
        incident["latitude"],
        incident["longitude"],
        incident["disaster_type"],
        incident["description"],
        incident["assistance"],
        incident["damage"],
        incident["damage_points"],
        incident["people_affected"],
        incident["life_safety"],
        incident["accessibility"],
        int(incident["immediate_threat"]),
        incident["safety_status"],
        incident["status"],
    ))

    assessed = calculate_priority(incident)

    return jsonify({
        "message": "Incident report received successfully.",
        "id": assessed["id"],
        "priority": assessed["priority"],
        "score": assessed["score"],
    }), 201


def next_incident_id():
    with get_db_connection() as connection:
        row = connection.execute("""
            SELECT MAX(CAST(SUBSTR(id, 5) AS INTEGER))
            FROM incidents
            WHERE id LIKE 'RQM-%'
        """).fetchone()

    next_number = (row[0] or 0) + 1
    return f"RQM-{next_number:03d}"

    with get_db_connection() as connection:
        rows = connection.execute(
            "SELECT id FROM incidents WHERE id LIKE 'RQM-%'"
        ).fetchall()

    numbers = []

    for row in rows:
        try:
            numbers.append(int(row["id"].split("-")[1]))
        except (IndexError, ValueError):
            continue

    next_number = max(numbers, default=0) + 1
    return f"RQM-{next_number:03d}"
@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "ResQMap AI"})
init_db()
@app.route("/api/incidents/<incident_id>/status", methods=["PATCH"])
def update_incident_status(incident_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    allowed_statuses = {
        "Pending inspection",
        "Field verified",
        "Resolved"
    }

    if new_status not in allowed_statuses:
        return jsonify({
            "error": "Invalid status",
            "allowed_statuses": sorted(allowed_statuses)
        }), 400

    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE incidents
            SET status = ?
            WHERE id = ?
            """,
            (new_status, incident_id)
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Incident not found"}), 404

    return jsonify({
        "message": "Incident status updated",
        "id": incident_id,
        "status": new_status
    }), 200

@app.route("/api/assess-damage", methods=["POST"])
def assess_damage():
    photo = request.files.get("photo")
    latitude = request.form.get("claimed_lat")
    longitude = request.form.get("claimed_lng")
    disaster_cutoff = request.form.get("disaster_cutoff")
    property_type = request.form.get("property_type", "building")

    if not photo or not photo.filename:
        return jsonify({"error": "Please upload a damage photo."}), 400

    if not latitude or not longitude or not disaster_cutoff:
        return jsonify({
            "error": "Photo, GPS coordinates, and disaster date/time are required."
        }), 400

    try:
        latitude = float(latitude)
        longitude = float(longitude)

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("Coordinates out of range")
    except ValueError:
        return jsonify({"error": "Enter valid GPS coordinates."}), 400

    try:
        response = requests.post(
            "https://aapdasetu-damage-api.onrender.com/api/assess-damage",
            files={
                "photo": (
                    photo.filename,
                    photo.stream,
                    photo.mimetype or "application/octet-stream"
                )
            },
            data={
                "claimed_lat": latitude,
                "claimed_lng": longitude,
                "property_type": property_type,
                "disaster_cutoff": disaster_cutoff,
            },
            timeout=90,
        )

        try:
            result = response.json()
        except ValueError:
            result = {"message": response.text[:1000]}

        if not response.ok:
            return jsonify({
                "error": "The AI service rejected the assessment.",
                "details": result,
            }), 502

        return jsonify({
            "message": "AI assessment completed.",
            "assessment": result,
        }), 200

    except requests.RequestException:
        return jsonify({
            "error": "The AI service could not be reached. Please try again."
        }), 502
if __name__ == "__main__":
    app.run(debug=True)