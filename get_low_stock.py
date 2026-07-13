import sqlite3, os

db_path = os.path.join('c:/Users/gupta/Downloads/urvashi/projects/med','medicines.db')
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT MedicineName, Quantity, MinStock, HospitalCode, ExpiryDate, BatchNo FROM vw_low_stock_alerts").fetchall()
print("| Medicine Name | Quantity | Min Stock | Hospital | Expiry Date | Batch No |")
print("|---|---|---|---|---|---|")
for r in rows:
    print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")
conn.close()
