import sqlite3
conn = sqlite3.connect('quiz.db')
cur = conn.cursor()
cur.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cur.fetchall()
print('Tables:', tables)

# Check questions table schema
cur.execute('PRAGMA table_info(questions)')
questions_schema = cur.fetchall()
print('Questions schema:', questions_schema)

# Check if there are questions
cur.execute('SELECT COUNT(*) FROM questions')
question_count = cur.fetchone()[0]
print('Total questions:', question_count)

conn.close()