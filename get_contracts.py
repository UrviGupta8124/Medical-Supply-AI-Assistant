import sqlite3, os

db_path = os.path.join('c:/Users/gupta/Downloads/urvashi/projects/med','medicines.db')
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT ContractID, MedicineName, Rate, TenderNo, QuotationNo, SupplierName FROM vw_active_contracts").fetchall()
print("| Contract ID | Medicine Name | Rate (INR) | Tender No | Quotation No | Supplier Name |")
print("|---|---|---|---|---|---|")
for r in rows:
    print(f"| {r[0]} | {r[1]} | {r[2]:.2f} | {r[3]} | {r[4]} | {r[5]} |")
conn.close()
