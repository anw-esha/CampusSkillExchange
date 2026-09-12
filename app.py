from flask import Flask, render_template, jsonify, request
import sqlite3

app = Flask(__name__)

DATABASE = "campus.db"


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    # Mentors
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

    # Requests
    conn.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentor_id INTEGER,
            junior_name TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    # Certificates
    conn.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentor_name TEXT,
            junior_name TEXT,
            skill TEXT,
            certificate_type TEXT
        )
    """)

    # Sample mentors
    count = conn.execute(
        "SELECT COUNT(*) FROM mentors"
    ).fetchone()[0]

    if count == 0:

        sample_mentors = [
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
        """, sample_mentors)

    # ---------------------------------
    # CHANGE OLD USER NAME
    # ---------------------------------

    conn.execute("""
        UPDATE requests
        SET junior_name = 'Anwesha Bhattacharjee'
        WHERE junior_name = 'Shibangi Paul'
    """)

    conn.execute("""
        UPDATE certificates
        SET junior_name = 'Anwesha Bhattacharjee'
        WHERE junior_name = 'Shibangi Paul'
    """)

    conn.commit()
    conn.close()


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# GET MENTORS
# =========================

@app.route("/api/mentors")
def get_mentors():

    conn = get_db()

    rows = conn.execute(
        "SELECT * FROM mentors"
    ).fetchall()

    conn.close()

    mentors = []

    for row in rows:

        mentors.append({
            "id": row["id"],
            "name": row["name"],
            "skills": row["skills"].split(","),
            "rating": row["rating"],
            "available": bool(row["available"]),
            "experience": row["experience"]
        })

    return jsonify(mentors)


# =========================
# SEARCH MENTORS
# =========================

@app.route("/api/mentors/search")
def search_mentors():

    skill = request.args.get(
        "skill",
        ""
    ).lower()

    conn = get_db()

    rows = conn.execute(
        "SELECT * FROM mentors"
    ).fetchall()

    conn.close()

    results = []

    for row in rows:

        skills = row["skills"].split(",")

        for mentor_skill in skills:

            if skill in mentor_skill.lower():

                results.append({
                    "id": row["id"],
                    "name": row["name"],
                    "skills": skills,
                    "rating": row["rating"],
                    "available": bool(
                        row["available"]
                    ),
                    "experience": row["experience"]
                })

                break

    return jsonify(results)


# =========================
# CREATE MENTOR PROFILE
# =========================

@app.route(
    "/api/profile",
    methods=["POST"]
)
def create_profile():

    data = request.get_json()

    name = data.get("name")

    skills = data.get(
        "skills",
        []
    )

    experience = data.get(
        "experience",
        "Beginner"
    )

    skills_text = ",".join(skills)

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO mentors
        (name, skills, rating, available, experience)
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
            "Profile saved permanently!",
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

    data = request.get_json()

    mentor_id = data.get(
        "mentor_id"
    )

    # ALWAYS USE THIS NAME
    junior_name = "Anwesha Bhattacharjee"

    conn = get_db()

    conn.execute("""
        INSERT INTO requests
        (mentor_id, junior_name, status)
        VALUES (?, ?, ?)
    """, (
        mentor_id,
        junior_name,
        "Pending"
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message":
            "Connection request sent successfully!"
    })


# =========================
# GET REQUESTS
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

    requests = []

    for row in rows:

        requests.append({
            "id": row["id"],
            "junior_name":
                row["junior_name"],
            "mentor_name":
                row["mentor_name"],
            "status":
                row["status"]
        })

    return jsonify(requests)


# =========================
# ACCEPT REQUEST
# =========================

@app.route(
    "/api/requests/<int:request_id>/accept",
    methods=["POST"]
)
def accept_request(request_id):

    conn = get_db()

    conn.execute("""
        UPDATE requests
        SET status = 'Accepted'
        WHERE id = ?
    """, (
        request_id,
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message":
            "Request accepted!"
    })


# =========================
# COMPLETE SESSION
# =========================

@app.route(
    "/api/requests/<int:request_id>/complete",
    methods=["POST"]
)
def complete_session(request_id):

    conn = get_db()

    row = conn.execute("""
        SELECT
            requests.id,
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
        })


    if row["status"] != "Accepted":

        conn.close()

        return jsonify({
            "success": False,
            "message":
                "Request must be accepted first."
        })


    # Complete request
    conn.execute("""
        UPDATE requests
        SET status = 'Completed'
        WHERE id = ?
    """, (
        request_id,
    ))


    # First skill
    skill = row["skills"].split(",")[0]


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
        "Anwesha Bhattacharjee",
        skill,
        "Mentor Contribution Badge"
    ))


    conn.commit()
    conn.close()


    return jsonify({
        "success": True,
        "message":
            "Learning session completed!",
        "certificate":
            "Mentor Contribution Badge"
    })


# =========================
# GET CERTIFICATES
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
            "id": row["id"],
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
# HEALTH CHECK
# =========================

@app.route("/health")
def health():

    return jsonify({
        "status": "healthy",
        "project":
            "Campus Skill Exchange",
        "university":
            "TECHNO INDIA UNIVERSITY"
    })


# =========================
# RUN APP
# =========================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True
    )