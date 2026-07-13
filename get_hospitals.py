import sqlite3, os

db_path = os.path.join('c:/Users/gupta/Downloads/urvashi/projects/med','medicines.db')
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT HospitalCode, HospitalName, Address, ContactNo FROM vw_registered_hospitals").fetchall()
print("| Hospital Code | Hospital Name | Address | Contact No |")
print("|---|---|---|---|")
for r in rows:
    print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |")
conn.close()
