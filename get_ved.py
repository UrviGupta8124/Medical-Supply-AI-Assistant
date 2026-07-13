import sqlite3, os

db_path = os.path.join('c:/Users/gupta/Downloads/urvashi/projects/med','medicines.db')
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT MedicineName, Quantity, VEDCategory, Criticality FROM ved").fetchall()
print("| Medicine Name | Quantity | VED Category | Criticality |")
print("|---|---|---|---|")
for r in rows:
    print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |")
conn.close()
