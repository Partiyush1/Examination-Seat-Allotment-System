from flask import Flask, render_template, request, jsonify
import sqlite3
from collections import deque

app = Flask(__name__)

DB_FILE = "exam_management.db"


# =========================
# DATABASE CONNECTION
# =========================
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# DATABASE INIT
# =========================
def init_db():

    conn = get_db_connection()

    conn.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT,
            semester TEXT,
            roll_no TEXT
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            rows INTEGER,
            cols INTEGER
        )
    ''')

    conn.commit()
    conn.close()


init_db()


# =========================
# HOME PAGE
# =========================
@app.route('/')
def index():
    return render_template('index.html')


# =========================
# ADD DATA
# =========================
@app.route('/api/add_data', methods=['POST'])
def add_data():

    data = request.json

    conn = get_db_connection()

    try:

        if data['type'] == 'student':

            branch = data['branch'].strip().upper()

            semester = data['semester']

            start = int(data['start_roll'])

            end = int(data['end_roll'])

            for roll in range(start, end + 1):

                conn.execute(
                    '''
                    INSERT INTO students
                    (branch, semester, roll_no)
                    VALUES (?, ?, ?)
                    ''',
                    (
                        branch,
                        semester,
                        str(roll)
                    )
                )

        else:

            conn.execute(
                '''
                INSERT OR REPLACE INTO rooms
                (name, rows, cols)
                VALUES (?, ?, ?)
                ''',
                (
                    data['name'],
                    int(data['rows']),
                    int(data['cols'])
                )
            )

        conn.commit()

        return jsonify({
            "status": "success"
        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        })

    finally:
        conn.close()


# =========================
# DELETE STUDENTS
# =========================
@app.route('/api/delete_students', methods=['POST'])
def delete_students():

    data = request.json

    conn = get_db_connection()

    if data.get('all'):

        conn.execute("DELETE FROM students")

    else:

        conn.execute(
            '''
            DELETE FROM students
            WHERE branch=? AND semester=?
            ''',
            (
                data['branch'],
                data['semester']
            )
        )

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success"
    })


# =========================
# DELETE ROOM
# =========================
@app.route('/api/delete_room', methods=['POST'])
def delete_room():

    data = request.json

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM rooms WHERE name=?",
        (data['name'],)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success"
    })


# =========================
# GET CONFIG
# =========================
@app.route('/api/get_config')
def get_config():

    conn = get_db_connection()

    groups = conn.execute('''
        SELECT
            branch,
            semester,
            COUNT(*) as count
        FROM students
        GROUP BY branch, semester
    ''').fetchall()

    rooms = conn.execute(
        "SELECT * FROM rooms"
    ).fetchall()

    conn.close()

    return jsonify({

        "groups": [dict(r) for r in groups],

        "rooms": [dict(r) for r in rooms]

    })


# =========================
# GET ROLLS
# =========================
@app.route('/api/get_rolls', methods=['POST'])
def get_rolls():

    data = request.json

    conn = get_db_connection()

    rolls = conn.execute(
        '''
        SELECT roll_no
        FROM students
        WHERE branch=? AND semester=?
        ''',
        (
            data['branch'],
            data['semester']
        )
    ).fetchall()

    conn.close()

    return jsonify([
        r['roll_no']
        for r in rolls
    ])


# =========================
# SEAT ALLOCATION
# =========================
@app.route('/api/allocate', methods=['POST'])
def allocate():

    data = request.json

    groups = data['groups']

    selected_rooms = data['rooms']

    # =====================
    # MIX STUDENTS
    # =====================

    all_students = []

    queues = [deque(g) for g in groups]

    while any(queues):

        for q in queues:

            if q:
                all_students.append(q.popleft())

    # =====================
    # CAPACITY
    # =====================

    total_capacity = 0

    for room in selected_rooms:

        total_capacity += (
            int(room['rows']) *
            int(room['cols'])
        )

    # =====================
    # ALLOCATION
    # =====================

    results = []

    student_pointer = 0

    for room in selected_rooms:

        rows = int(room['rows'])

        cols = int(room['cols'])

        seating_plan = []

        for r in range(rows):

            row_data = []

            for c in range(cols):

                if student_pointer < len(all_students):

                    row_data.append(
                        all_students[student_pointer]
                    )

                    student_pointer += 1

                else:

                    row_data.append("EMPTY")

            seating_plan.append(row_data)

        results.append({

            "name": room['name'],

            "plan": seating_plan

        })

    # =====================
    # UNALLOCATED
    # =====================

    unallocated_students = []

    if student_pointer < len(all_students):

        unallocated_students = (
            all_students[student_pointer:]
        )

    return jsonify({

        "results": results,

        "total_students": len(all_students),

        "total_capacity": total_capacity,

        "allocated_students":
            min(len(all_students), total_capacity),

        "empty_seats":
            max(0, total_capacity - len(all_students)),

        "unallocated_students":
            unallocated_students,

        "unallocated_count":
            len(unallocated_students)

    })


# =========================
# RUN APP
# =========================
if __name__ == '__main__':

    app.run(debug=True)