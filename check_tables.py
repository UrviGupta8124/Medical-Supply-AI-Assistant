import sqlite3, os

db_path = os.path.join('c:/Users/gupta/Downloads/urvashi/projects/med','medicines.db')
conn = sqlite3.connect(db_path)
total_inv = conn.execute('SELECT COUNT(*) FROM vw_medicine_inventory').fetchone()[0]
total_low = conn.execute('SELECT COUNT(*) FROM vw_low_stock_alerts').fetchone()[0]

print(f"Total rows in vw_medicine_inventory: {total_inv}")
print(f"Total rows in vw_low_stock_alerts: {total_low}")

# Let's find where 'Epinephrine Plus 411mg' is in the full inventory
epi_rows = conn.execute("SELECT MedicineName, Quantity, MinStock FROM vw_medicine_inventory WHERE MedicineName LIKE 'Epinephrine%'").fetchall()
print("Epinephrine rows in inventory:")
for row in epi_rows:
    print(row)

conn.close()
