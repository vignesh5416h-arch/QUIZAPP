from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT, attempts INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY, question TEXT, op1 TEXT, op2 TEXT, op3 TEXT, op4 TEXT, answer TEXT, level TEXT DEFAULT 'easy', category TEXT DEFAULT 'General')")
    cur.execute("CREATE TABLE IF NOT EXISTS scores (id INTEGER PRIMARY KEY, username TEXT, score REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, level TEXT, category TEXT, total_questions INTEGER)")

    # Default admin
    cur.execute("INSERT OR IGNORE INTO users (id, username, password, role, attempts) VALUES (1, 'admin', 'admin123', 'admin', 0)")

    # Ensure questions table has the required columns for older databases
    cur.execute("PRAGMA table_info(questions)")
    columns = [row[1] for row in cur.fetchall()]
    if 'level' not in columns:
        cur.execute("ALTER TABLE questions ADD COLUMN level TEXT DEFAULT 'easy'")
        cur.execute("UPDATE questions SET level='easy' WHERE level IS NULL")
    if 'category' not in columns:
        cur.execute("ALTER TABLE questions ADD COLUMN category TEXT DEFAULT 'General'")
        cur.execute("UPDATE questions SET category='General' WHERE category IS NULL")

    # Update scores table schema if needed
    cur.execute("PRAGMA table_info(scores)")
    score_columns = [row[1] for row in cur.fetchall()]
    if 'timestamp' not in score_columns:
        cur.execute("ALTER TABLE scores ADD COLUMN timestamp TEXT")
    if 'level' not in score_columns:
        cur.execute("ALTER TABLE scores ADD COLUMN level TEXT")
    if 'category' not in score_columns:
        cur.execute("ALTER TABLE scores ADD COLUMN category TEXT")
    if 'total_questions' not in score_columns:
        cur.execute("ALTER TABLE scores ADD COLUMN total_questions INTEGER")

    # Seed sample questions if each level has fewer than 5 entries
    sample_questions = {
        'easy': [
            ("What is the capital of France?", "Paris", "London", "Berlin", "Madrid", "Paris", "easy", "General"),
            ("Which number is even?", "3", "5", "8", "11", "8", "easy", "Aptitude"),
            ("What color do you get when you mix red and white?", "Pink", "Green", "Blue", "Orange", "Pink", "easy", "General"),
            ("How many legs does a spider have?", "6", "8", "10", "12", "8", "easy", "General"),
            ("What is 5 + 3?", "7", "8", "9", "10", "8", "easy", "Aptitude"),
        ],
        'medium': [
            ("What is the square root of 144?", "10", "11", "12", "14", "12", "medium", "Aptitude"),
            ("Which planet is known as the Red Planet?", "Earth", "Venus", "Mars", "Jupiter", "Mars", "medium", "Science"),
            ("Which gas do plants absorb during photosynthesis?", "Oxygen", "Carbon Dioxide", "Nitrogen", "Argon", "Carbon Dioxide", "medium", "Science"),
            ("What is 15% of 200?", "20", "25", "30", "35", "30", "medium", "Aptitude"),
            ("Who painted the Mona Lisa?", "Vincent van Gogh", "Pablo Picasso", "Leonardo da Vinci", "Claude Monet", "Leonardo da Vinci", "medium", "General"),
        ],
        'hard': [
            ("What is the derivative of x^2?", "x", "2x", "x^2", "2", "2x", "hard", "Science"),
            ("Who wrote the play 'Macbeth'?", "Charles Dickens", "William Shakespeare", "Jane Austen", "Mark Twain", "William Shakespeare", "hard", "General"),
            ("What is the chemical symbol for gold?", "Ag", "Au", "Gd", "Go", "Au", "hard", "Science"),
            ("What is the value of pi to 2 decimal places?", "3.12", "3.14", "3.16", "3.18", "3.14", "hard", "Math"),
            ("What is the smallest prime number greater than 50?", "51", "53", "55", "57", "53", "hard", "Aptitude"),
        ],
    }

    for level, questions in sample_questions.items():
        cur.execute("SELECT COUNT(*) FROM questions WHERE level=?", (level,))
        current_count = cur.fetchone()[0]
        if current_count < 5:
            needed = 5 - current_count
            cur.executemany(
                "INSERT INTO questions (question, op1, op2, op3, op4, answer, level, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                questions[:needed]
            )

    conn.commit()
    conn.close()

init_db()

# ---------------- HELPERS ----------------
def get_categories():
    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM questions")
    categories = [row[0] for row in cur.fetchall()]
    conn.close()
    if not categories:
        categories = ["General", "Aptitude", "Science", "Math", "Python", "C"]
    return categories

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect("quiz.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = u
            session["role"] = user[3]

            if user[3] == "admin":
                return redirect("/admin")
            else:
                return redirect("/student_panel")

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect("quiz.db")
        cur = conn.cursor()
        
        # Check if username already exists
        cur.execute("SELECT * FROM users WHERE username=?", (u,))
        existing_user = cur.fetchone()
        
        if existing_user:
            conn.close()
            return render_template("register.html", error="Username already exists!")
        
        # Insert new user
        cur.execute("INSERT INTO users (username, password, role, attempts) VALUES (?, ?, 'student', 0)", (u, p))
        conn.commit()
        conn.close()
        
        return redirect("/")
    
    return render_template("register.html")

# ---------------- STUDENT PANEL ----------------
@app.route("/student_panel")
def student_panel():
    if session.get("role") != "student":
        return redirect("/")

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM questions")
    categories = [row[0] for row in cur.fetchall()]
    conn.close()

    return render_template("student_panel.html", categories=categories)

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/")
    
    # Get user statistics
    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()
    cur.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
    user_stats = dict(cur.fetchall())
    conn.close()
    
    return render_template("admin.html", user_stats=user_stats)

@app.route("/manage_questions")
def manage_questions():
    if session.get("role") != "admin":
        return redirect("/")

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions ORDER BY id DESC")
    questions = cur.fetchall()
    conn.close()

    return render_template("manage_questions.html", questions=questions)

@app.route("/edit_question/<int:q_id>", methods=["GET", "POST"])
def edit_question(q_id):
    if session.get("role") != "admin":
        return redirect("/")

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    if request.method == "POST":
        q = request.form["q"]
        op1 = request.form["op1"]
        op2 = request.form["op2"]
        op3 = request.form["op3"]
        op4 = request.form["op4"]
        ans = request.form["ans"]
        level = request.form["level"]
        category = request.form.get("category", "General")

        cur.execute(
            "UPDATE questions SET question=?, op1=?, op2=?, op3=?, op4=?, answer=?, level=?, category=? WHERE id=?",
            (q, op1, op2, op3, op4, ans, level, category, q_id)
        )
        conn.commit()
        conn.close()
        return redirect("/manage_questions")

    cur.execute("SELECT * FROM questions WHERE id=?", (q_id,))
    question = cur.fetchone()
    conn.close()
    return render_template("edit_question.html", question=question)

@app.route("/delete_question/<int:q_id>")
def delete_question(q_id):
    if session.get("role") != "admin":
        return redirect("/")

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM questions WHERE id=?", (q_id,))
    conn.commit()
    conn.close()
    return redirect("/manage_questions")

# CREATE QUIZ
@app.route("/create", methods=["GET", "POST"])
def create():
    if session.get("role") != "admin":
        return redirect("/")
    
    if request.method == "POST":
        q = request.form["q"]
        op1 = request.form["op1"]
        op2 = request.form["op2"]
        op3 = request.form["op3"]
        op4 = request.form["op4"]
        ans = request.form["ans"]
        level = request.form["level"]
        category = request.form.get("category", "General")

        conn = sqlite3.connect("quiz.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO questions (question, op1, op2, op3, op4, answer, level, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (q, op1, op2, op3, op4, ans, level, category))
        conn.commit()
        conn.close()

    return render_template("create_quiz.html")

# ---------------- QUIZ ----------------
@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if session.get("role") != "student":
        return redirect("/")
    
    level = request.args.get('level', 'easy')
    category = request.args.get('category', 'General')
    
    if session.get("level") != level or session.get("category") != category or "questions" not in session:
        session["level"] = level
        session["category"] = category
        session["qno"] = 0
        session["score"] = 0.0
        session["feedback"] = None
        session["answers"] = []

        conn = sqlite3.connect("quiz.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM questions WHERE level=? AND category=?", (level, category))
        data = [list(row) for row in cur.fetchall()]
        conn.close()

        if len(data) == 0:
            return render_template("student_panel.html", error=f"No {category} {level} questions are available yet. Please choose another category or level.", categories=get_categories())

        random.shuffle(data)
        session["questions"] = data
    else:
        data = session["questions"]

    if request.method == "POST":
        qno = session["qno"]
        current = data[qno]
        selected = request.form.get("answer", "")
        correct = current[6]
        positive_mark = 1.0
        negative_mark = -0.25

        if selected == correct:
            session["score"] += positive_mark
            feedback = "Correct! +1"
            points = positive_mark
        else:
            session["score"] += negative_mark
            feedback = f"Wrong! Correct answer: {correct} (-0.25)"
            points = negative_mark

        session["answers"].append({
            "question": current[1],
            "selected": selected,
            "correct": correct,
            "is_correct": selected == correct,
            "points": points,
            "level": current[7],
            "category": current[8],
        })
        session["qno"] += 1
        session["feedback"] = feedback

    if session["qno"] >= len(data):
        score = session["score"]

        conn = sqlite3.connect("quiz.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO scores (username, score, timestamp, level, category, total_questions) VALUES (?, ?, ?, ?, ?, ?)",
                    (session["user"], score, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), level, category, len(data)))
        conn.commit()
        conn.close()

        return redirect("/result")

    q = data[session["qno"]]
    feedback = session.get("feedback")
    remaining_time = 60
    return render_template(
        "quiz.html",
        q=q,
        feedback=feedback,
        question_number=session["qno"]+1,
        total_questions=len(data),
        level=level,
        category=category,
        remaining_time=remaining_time,
        negative_mark=-0.25,
    )

# ---------------- RESULT ----------------
@app.route("/result")
def result():
    score = session.get("score", 0)
    answers = session.get("answers", [])
    level = session.get("level", "")
    category = session.get("category", "")
    
    # Calculate statistics
    total_questions = len(answers)
    correct_count = sum(1 for answer in answers if answer.get("is_correct", False))
    wrong_count = total_questions - correct_count
    
    session.clear()
    return render_template("result.html", score=score, answers=answers, level=level, category=category, 
                         total_questions=total_questions, correct_count=correct_count, wrong_count=wrong_count)

# ---------------- LEADERBOARD ----------------
@app.route("/leaderboard")
def leaderboard():
    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()
    cur.execute("SELECT username, MAX(score) FROM scores GROUP BY username ORDER BY MAX(score) DESC")
    data = cur.fetchall()
    conn.close()

    return render_template("leaderboard.html", data=data)

# ---------------- QUIZ HISTORY ----------------
@app.route("/quiz_history")
def quiz_history():
    if "user" not in session:
        return redirect("/")
    
    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()
    # Only get records that have complete data (newer records with timestamp, level, category, total_questions)
    cur.execute("SELECT timestamp, score, level, category, total_questions FROM scores WHERE username=? AND timestamp IS NOT NULL ORDER BY timestamp DESC", (session["user"],))
    history_data = cur.fetchall()
    conn.close()

    return render_template("quiz_history.html", history=history_data)

# ---------------- CATEGORY LEADERBOARD ----------------
@app.route("/category_leaderboard")
def category_leaderboard():
    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()
    
    # Get all categories that have scores
    cur.execute("SELECT DISTINCT category FROM scores WHERE category IS NOT NULL ORDER BY category")
    categories = [row[0] for row in cur.fetchall()]
    
    # Get leaderboard data for each category
    category_data = {}
    for category in categories:
        cur.execute("""
            SELECT username, MAX(score) as max_score, COUNT(*) as attempts
            FROM scores 
            WHERE category=? 
            GROUP BY username 
            ORDER BY max_score DESC, attempts DESC
            LIMIT 10
        """, (category,))
        category_data[category] = cur.fetchall()
    
    conn.close()
    
    return render_template("category_leaderboard.html", category_data=category_data, categories=categories)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)