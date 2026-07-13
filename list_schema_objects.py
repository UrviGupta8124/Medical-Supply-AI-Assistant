import sqlite3, os

db_path = os.path.join('c:/Users/gupta/Downloads/urvashi/projects/med','medicines.db')
conn = sqlite3.connect(db_path)

# List all tables
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("=== BASE TABLES ===")
for t in tables:
    print(t[0])

# List all views
views = conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
print("\n=== SQL VIEWS ===")
for v in views:
    print(v[0])

conn.close()
