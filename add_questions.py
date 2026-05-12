import sqlite3

conn = sqlite3.connect("quiz.db")
cur = conn.cursor()

# Add 2 questions
cur.execute("INSERT INTO questions (question, op1, op2, op3, op4, answer) VALUES (?, ?, ?, ?, ?, ?)",
            ("What is the capital of France?", "Paris", "London", "Berlin", "Madrid", "Paris"))
cur.execute("INSERT INTO questions (question, op1, op2, op3, op4, answer) VALUES (?, ?, ?, ?, ?, ?)",
            ("What is 2 + 2?", "3", "4", "5", "6", "4"))


conn.commit()
conn.close()

print("Added 2 questions successfully!")








