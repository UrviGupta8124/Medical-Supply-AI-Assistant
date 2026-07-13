import sqlite3, os, json

db_path = os.path.join('c:/Users/gupta/Downloads/urvashi/projects/med','medicines.db')
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT MedicineName, Quantity FROM vw_medicine_inventory LIMIT 20").fetchall()
chart_data = [{"name": r[0], "value": r[1]} for r in rows]
print(json.dumps(chart_data, indent=2))
conn.close()
