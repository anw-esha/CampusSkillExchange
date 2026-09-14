from flask import Flask, render_template, jsonify, request
import sqlite3

app = Flask(__name__)

DATABASE = "campus.db"
JUNIOR_NAME = "Anwesha Bhattacharjee"


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    # -------------------------
    # MENTORS
    # -------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS mentors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            skills TEXT NOT NULL,
            rating REAL DEFAULT 5.0,
            available INTEGER DEFAULT 1,
            experience TEXT
        )
    """)

    # -------------------------
    # REQUESTS
    # -------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentor_id INTEGER,
            junior_name TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    # -------------------------
    # CERTIFICATES
    # -------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentor_name TEXT,
            junior_name TEXT,
            skill TEXT,
            certificate_type TEXT
        )
    """)

    # -------------------------
    # LEARNING PROGRESS
    # -------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            junior_name TEXT,
            skill TEXT,
            progress INTEGER DEFAULT 0
        )
    """)

    # -------------------------
    # DOUBT DESK
    # -------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS doubts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            junior_name TEXT,
            question TEXT,
            status TEXT DEFAULT 'Open'
        )
    """)

    # -------------------------
    # DEFAULT MENTORS
    # -------------------------

    count = conn.execute(
        "SELECT COUNT(*) FROM mentors"
    ).fetchone()[0]

    if count == 0:

        mentors = [
            (
                "Ananya Sharma",
                "Python,AI/ML",
                4.8,
                1,
                "2 years"
            ),
            (
                "Rahul Das",
                "C++,C",
                4.7,
                1,
                "1.5 years"
            ),
            (
                "Arjun Roy",
                "Java,Web Development",
                4.9,
                1,
                "2 years"
            )
        ]

        conn.executemany("""
            INSERT INTO mentors
            (name, skills, rating, available, experience)
            VALUES (?, ?, ?, ?, ?)
        """, mentors)

    # -------------------------
    # OLD NAME CORRECTION
    # -------------------------

    conn.execute("""
        UPDATE requests
        SET junior_name = ?
        WHERE junior_name IN
        ('Shibangi Paul', 'Campus Junior')
    """, (JUNIOR_NAME,))

    conn.execute("""
        UPDATE certificates
        SET junior_name = ?
        WHERE junior_name IN
        ('Shibangi Paul', 'Campus Junior')
    """, (JUNIOR_NAME,))

    conn.commit()
    conn.close()


# =========================
# SMART MATCHING ENGINE
# =========================

def calculate_match_score(
    mentor,
    requested_skill=""
):

    score = 0

    requested_skill = (
        requested_skill
        .strip()
        .lower()
    )

    skills = [
        s.strip().lower()
        for s in mentor["skills"].split(",")
    ]

    # 1. Skill match
    if requested_skill:

        if any(
            requested_skill in skill
            or skill in requested_skill
            for skill in skills
        ):
            score += 50

    # 2. Availability
    if mentor["available"]:
        score += 20

    # 3. Rating
    score += (
        float(mentor["rating"]) / 5
    ) * 20

    # 4. Experience
    experience = (
        mentor["experience"] or ""
    ).lower()

    if "2 years" in experience:
        score += 10

    elif "3 years" in experience:
        score += 10

    elif "4 years" in experience:
        score += 10

    elif "5 years" in experience:
        score += 10

    elif "year" in experience:
        score += 5

    return round(
        min(score, 100),
        1
    )


def mentor_to_dict(
    row,
    requested_skill=""
):

    return {
        "id": row["id"],
        "name": row["name"],
        "skills":
            row["skills"].split(","),
        "rating":
            row["rating"],
        "available":
            bool(row["available"]),
        "experience":
            row["experience"],
        "match_score":
            calculate_match_score(
                row,
                requested_skill
            )
    }


# =========================
# HOME
# =========================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================
# GET MENTORS
# =========================

@app.route("/api/mentors")
def get_mentors():

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM mentors
    """).fetchall()

    conn.close()

    mentors = [
        mentor_to_dict(row)
        for row in rows
    ]

    # Highest smart-match score first
    mentors.sort(
        key=lambda x:
        x["match_score"],
        reverse=True
    )

    return jsonify(mentors)


# =========================
# SMART SEARCH
# =========================

@app.route(
    "/api/mentors/search"
)
def search_mentors():

    skill = request.args.get(
        "skill",
        ""
    ).strip().lower()

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM mentors
    """).fetchall()

    conn.close()

    results = []

    for row in rows:

        skills = [
            s.strip().lower()
            for s in row["skills"].split(",")
        ]

        if (
            not skill
            or any(
                skill in s
                or s in skill
                for s in skills
            )
        ):

            results.append(
                mentor_to_dict(
                    row,
                    skill
                )
            )

    # Smart ranking
    results.sort(
        key=lambda x:
        x["match_score"],
        reverse=True
    )

    return jsonify(results)


# =========================
# SMART RECOMMENDATION
# =========================

@app.route(
    "/api/recommendations"
)
def recommendations():

    skill = request.args.get(
        "skill",
        ""
    )

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM mentors
    """).fetchall()

    conn.close()

    recommendations = [
        mentor_to_dict(
            row,
            skill
        )
        for row in rows
    ]

    recommendations.sort(
        key=lambda x:
        x["match_score"],
        reverse=True
    )

    return jsonify(
        recommendations[:5]
    )


# =========================
# CREATE PROFILE
# =========================

@app.route(
    "/api/profile",
    methods=["POST"]
)
def create_profile():

    data = request.get_json() or {}

    name = data.get(
        "name",
        ""
    ).strip()

    skills = data.get(
        "skills",
        []
    )

    experience = data.get(
        "experience",
        "Beginner"
    )

    if not name or not skills:

        return jsonify({
            "success": False,
            "message":
                "Name and skills are required."
        }), 400

    skills_text = ",".join(
        skills
    )

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO mentors
        (
            name,
            skills,
            rating,
            available,
            experience
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        name,
        skills_text,
        5.0,
        1,
        experience
    ))

    conn.commit()

    new_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "success": True,
        "message":
            "Mentor profile saved permanently!",
        "id": new_id
    })


# =========================
# CONNECT
# =========================

@app.route(
    "/api/connect",
    methods=["POST"]
)
def connect():

    data = request.get_json() or {}

    mentor_id = data.get(
        "mentor_id"
    )

    if not mentor_id:

        return jsonify({
            "success": False,
            "message":
                "Mentor ID is required."
        }), 400

    conn = get_db()

    # Prevent duplicate pending request
    existing = conn.execute("""
        SELECT id
        FROM requests
        WHERE mentor_id = ?
        AND junior_name = ?
        AND status IN
        ('Pending', 'Accepted')
    """, (
        mentor_id,
        JUNIOR_NAME
    )).fetchone()

    if existing:

        conn.close()

        return jsonify({
            "success": False,
            "message":
                "You already have an active request."
        })

    conn.execute("""
        INSERT INTO requests
        (
            mentor_id,
            junior_name,
            status
        )
        VALUES (?, ?, ?)
    """, (
        mentor_id,
        JUNIOR_NAME,
        "Pending"
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message":
            "Smart connection request sent!"
    })


# =========================
# REQUESTS
# =========================

@app.route("/api/requests")
def get_requests():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            requests.id,
            requests.junior_name,
            requests.status,
            mentors.name AS mentor_name
        FROM requests
        JOIN mentors
        ON requests.mentor_id = mentors.id
        ORDER BY requests.id DESC
    """).fetchall()

    conn.close()

    result = []

    for row in rows:

        result.append({
            "id":
                row["id"],
            "junior_name":
                row["junior_name"],
            "mentor_name":
                row["mentor_name"],
            "status":
                row["status"]
        })

    return jsonify(result)


# =========================
# ACCEPT REQUEST
# =========================

@app.route(
    "/api/requests/<int:request_id>/accept",
    methods=["POST"]
)
def accept_request(
    request_id
):

    conn = get_db()

    cursor = conn.execute("""
        UPDATE requests
        SET status = 'Accepted'
        WHERE id = ?
        AND status = 'Pending'
    """, (
        request_id,
    ))

    conn.commit()

    updated = cursor.rowcount

    conn.close()

    if updated == 0:

        return jsonify({
            "success": False,
            "message":
                "Request is no longer pending."
        }), 400

    return jsonify({
        "success": True,
        "message":
            "Request accepted successfully!"
    })


# =========================
# COMPLETE SESSION
# =========================

@app.route(
    "/api/requests/<int:request_id>/complete",
    methods=["POST"]
)
def complete_session(
    request_id
):

    conn = get_db()

    row = conn.execute("""
        SELECT
            requests.junior_name,
            requests.status,
            mentors.name AS mentor_name,
            mentors.skills
        FROM requests
        JOIN mentors
        ON requests.mentor_id = mentors.id
        WHERE requests.id = ?
    """, (
        request_id,
    )).fetchone()

    if row is None:

        conn.close()

        return jsonify({
            "success": False,
            "message":
                "Request not found."
        }), 404

    if row["status"] != "Accepted":

        conn.close()

        return jsonify({
            "success": False,
            "message":
                "Accept the request first."
        }), 400

    # Complete request
    conn.execute("""
        UPDATE requests
        SET status = 'Completed'
        WHERE id = ?
    """, (
        request_id,
    ))

    skill = (
        row["skills"]
        .split(",")[0]
        .strip()
    )

    # Create certificate
    conn.execute("""
        INSERT INTO certificates
        (
            mentor_name,
            junior_name,
            skill,
            certificate_type
        )
        VALUES (?, ?, ?, ?)
    """, (
        row["mentor_name"],
        row["junior_name"],
        skill,
        "Mentor Contribution Badge"
    ))

    # Update learning progress
    existing_progress = conn.execute("""
        SELECT id, progress
        FROM progress
        WHERE junior_name = ?
        AND skill = ?
    """, (
        row["junior_name"],
        skill
    )).fetchone()

    if existing_progress:

        new_progress = min(
            existing_progress["progress"] + 25,
            100
        )

        conn.execute("""
            UPDATE progress
            SET progress = ?
            WHERE id = ?
        """, (
            new_progress,
            existing_progress["id"]
        ))

    else:

        conn.execute("""
            INSERT INTO progress
            (
                junior_name,
                skill,
                progress
            )
            VALUES (?, ?, ?)
        """, (
            row["junior_name"],
            skill,
            25
        ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message":
            "Mentoring session completed!",
        "certificate":
            "Mentor Contribution Badge"
    })


# =========================
# CERTIFICATES
# =========================

@app.route("/api/certificates")
def get_certificates():

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM certificates
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    certificates = []

    for row in rows:

        certificates.append({
            "id":
                row["id"],
            "mentor_name":
                row["mentor_name"],
            "junior_name":
                row["junior_name"],
            "skill":
                row["skill"],
            "certificate_type":
                row["certificate_type"]
        })

    return jsonify(certificates)


# =========================
# LEARNING PROGRESS
# =========================

@app.route(
    "/api/progress"
)
def get_progress():

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM progress
        WHERE junior_name = ?
        ORDER BY id DESC
    """, (
        JUNIOR_NAME,
    )).fetchall()

    conn.close()

    progress = []

    for row in rows:

        progress.append({
            "skill":
                row["skill"],
            "progress":
                row["progress"]
        })

    return jsonify(progress)


# =========================
# DOUBT DESK
# =========================

@app.route(
    "/api/doubts",
    methods=["POST"]
)
def create_doubt():

    data = request.get_json() or {}

    question = data.get(
        "question",
        ""
    ).strip()

    if not question:

        return jsonify({
            "success": False,
            "message":
                "Please enter your question."
        }), 400

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO doubts
        (
            junior_name,
            question,
            status
        )
        VALUES (?, ?, ?)
    """, (
        JUNIOR_NAME,
        question,
        "Open"
    ))

    conn.commit()

    doubt_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "success": True,
        "message":
            "Doubt submitted successfully!",
        "id":
            doubt_id
    })


@app.route(
    "/api/doubts"
)
def get_doubts():

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM doubts
        WHERE junior_name = ?
        ORDER BY id DESC
    """, (
        JUNIOR_NAME,
    )).fetchall()

    conn.close()

    doubts = []

    for row in rows:

        doubts.append({
            "id":
                row["id"],
            "question":
                row["question"],
            "status":
                row["status"]
        })

    return jsonify(doubts)


# =========================
# RUN
# =========================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True
    )