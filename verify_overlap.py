import sqlite3, os

db_path = os.path.join('c:/Users/gupta/Downloads/urvashi/projects/med','medicines.db')
conn = sqlite3.connect(db_path)

# Let's get all medicines in vw_low_stock_alerts
low_stock_meds = conn.execute("SELECT MedicineName, Quantity, MinStock, BatchNo FROM vw_low_stock_alerts").fetchall()

# Let's get all medicines in vw_medicine_inventory
all_meds = conn.execute("SELECT MedicineName, Quantity, MinStock, BatchNo FROM vw_medicine_inventory").fetchall()

all_med_set = set(all_meds)

print("Checking if any low stock medicine is missing from the general medicine inventory...")
missing_count = 0
for med in low_stock_meds:
    if med not in all_med_set:
        print(f"MISSING: {med}")
        missing_count += 1

if missing_count == 0:
    print("SUCCESS: Every single low-stock medicine is present in the medicine inventory table!")
else:
    print(f"FAILED: {missing_count} medicines are in low_stock but NOT in inventory.")

conn.close()
